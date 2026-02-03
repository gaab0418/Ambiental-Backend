import { Test, TestingModule } from '@nestjs/testing';
import { AuthService } from './auth.service';
import { UsersService } from '../users/users.service';
import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';
import { PrismaService } from '../../shared/prisma/prisma.service';
import { ConflictException, UnauthorizedException } from '@nestjs/common';
import * as bcrypt from 'bcrypt';

// Mocks
const mockUsersService = {
	findByEmail: jest.fn(),
	findById: jest.fn(),
	create: jest.fn(),
};

const mockJwtService = {
	sign: jest.fn().mockReturnValue('mock-jwt-token'),
};

const mockConfigService = {
	get: jest.fn((key: string, defaultValue?: string) => {
		const config: Record<string, string> = {
			PASSWORD_PEPPER: 'test-pepper',
			JWT_ACCESS_EXPIRATION: '15m',
			JWT_REFRESH_EXPIRATION: '30d',
		};
		return config[key] || defaultValue;
	}),
};

const mockPrismaService = {
	refreshToken: {
		create: jest.fn(),
		findUnique: jest.fn(),
		update: jest.fn(),
		updateMany: jest.fn(),
	},
};

describe('AuthService', () => {
	let service: AuthService;

	const mockUser = {
		id: 'user-123',
		email: 'test@example.com',
		password: '', // Será definido com hash
		name: 'Test User',
		role: 'USER' as const,
		isActive: true,
		createdAt: new Date(),
		updatedAt: new Date(),
	};

	beforeEach(async () => {
		// Gerar hash real para testes
		const pepperedPassword = 'TestPass@123test-pepper';
		mockUser.password = await bcrypt.hash(pepperedPassword, 10);

		const module: TestingModule = await Test.createTestingModule({
			providers: [
				AuthService,
				{ provide: UsersService, useValue: mockUsersService },
				{ provide: JwtService, useValue: mockJwtService },
				{ provide: ConfigService, useValue: mockConfigService },
				{ provide: PrismaService, useValue: mockPrismaService },
			],
		}).compile();

		service = module.get<AuthService>(AuthService);

		// Resetar mocks
		jest.clearAllMocks();
	});

	describe('validateUser', () => {
		it('deve retornar usuário com credenciais válidas', async () => {
			mockUsersService.findByEmail.mockResolvedValue(mockUser);

			const result = await service.validateUser(
				'test@example.com',
				'TestPass@123',
			);

			expect(result).toBeDefined();
			expect(result?.email).toBe('test@example.com');
		});

		it('deve retornar null se usuário não existe', async () => {
			mockUsersService.findByEmail.mockResolvedValue(null);

			const result = await service.validateUser(
				'naoexiste@example.com',
				'qualquer',
			);

			expect(result).toBeNull();
		});

		it('deve retornar null se senha incorreta', async () => {
			mockUsersService.findByEmail.mockResolvedValue(mockUser);

			const result = await service.validateUser(
				'test@example.com',
				'senha-errada',
			);

			expect(result).toBeNull();
		});

		it('deve lançar erro se usuário inativo', async () => {
			const inactiveUser = { ...mockUser, isActive: false };
			mockUsersService.findByEmail.mockResolvedValue(inactiveUser);

			await expect(
				service.validateUser('test@example.com', 'TestPass@123'),
			).rejects.toThrow(UnauthorizedException);
		});
	});

	describe('login', () => {
		it('deve retornar tokens e usuário', async () => {
			mockPrismaService.refreshToken.create.mockResolvedValue({
				id: 'token-id',
				token: 'refresh-token',
			});

			const result = await service.login(mockUser);

			expect(result).toHaveProperty('access_token');
			expect(result).toHaveProperty('refresh_token');
			expect(result).toHaveProperty('user');
			expect(result.user).not.toHaveProperty('password');
		});
	});

	describe('register', () => {
		it('deve criar usuário e retornar tokens', async () => {
			mockUsersService.findByEmail.mockResolvedValue(null);
			mockUsersService.create.mockResolvedValue(mockUser);
			mockPrismaService.refreshToken.create.mockResolvedValue({
				id: 'token-id',
				token: 'refresh-token',
			});

			const result = await service.register({
				email: 'novo@example.com',
				password: 'NewPass@123',
				name: 'Novo User',
			});

			expect(result).toHaveProperty('access_token');
			expect(result).toHaveProperty('refresh_token');
			expect(mockUsersService.create).toHaveBeenCalled();
		});

		it('deve lançar erro se email já existe', async () => {
			mockUsersService.findByEmail.mockResolvedValue(mockUser);

			await expect(
				service.register({
					email: 'test@example.com',
					password: 'Pass@123',
					name: 'Test',
				}),
			).rejects.toThrow(ConflictException);
		});
	});

	describe('refreshTokens', () => {
		const mockStoredToken = {
			id: 'token-id',
			token: 'valid-refresh-token',
			userId: 'user-123',
			expiresAt: new Date(Date.now() + 86400000), // +1 dia
			isRevoked: false,
			user: mockUser,
		};

		it('deve renovar tokens com sucesso', async () => {
			mockPrismaService.refreshToken.findUnique.mockResolvedValue(
				mockStoredToken,
			);
			mockPrismaService.refreshToken.update.mockResolvedValue({});
			mockPrismaService.refreshToken.create.mockResolvedValue({});

			const result = await service.refreshTokens('valid-refresh-token');

			expect(result).toHaveProperty('access_token');
			expect(result).toHaveProperty('refresh_token');
			expect(mockPrismaService.refreshToken.update).toHaveBeenCalledWith({
				where: { id: 'token-id' },
				data: { isRevoked: true },
			});
		});

		it('deve lançar erro com token inválido', async () => {
			mockPrismaService.refreshToken.findUnique.mockResolvedValue(null);

			await expect(
				service.refreshTokens('invalid-token'),
			).rejects.toThrow(UnauthorizedException);
		});

		it('deve lançar erro com token revogado', async () => {
			mockPrismaService.refreshToken.findUnique.mockResolvedValue({
				...mockStoredToken,
				isRevoked: true,
			});

			await expect(
				service.refreshTokens('revoked-token'),
			).rejects.toThrow(UnauthorizedException);
		});

		it('deve lançar erro com token expirado', async () => {
			mockPrismaService.refreshToken.findUnique.mockResolvedValue({
				...mockStoredToken,
				expiresAt: new Date(Date.now() - 86400000), // -1 dia
			});

			await expect(
				service.refreshTokens('expired-token'),
			).rejects.toThrow(UnauthorizedException);
		});
	});

	describe('logout', () => {
		it('deve revogar token', async () => {
			mockPrismaService.refreshToken.findUnique.mockResolvedValue({
				id: 'token-id',
				token: 'token',
			});
			mockPrismaService.refreshToken.update.mockResolvedValue({});

			const result = await service.logout('token');

			expect(result.message).toContain('Logout');
			expect(mockPrismaService.refreshToken.update).toHaveBeenCalled();
		});

		it('deve retornar sucesso mesmo com token inexistente', async () => {
			mockPrismaService.refreshToken.findUnique.mockResolvedValue(null);

			const result = await service.logout('inexistente');

			expect(result.message).toContain('Logout');
		});
	});

	describe('logoutAll', () => {
		it('deve revogar todos os tokens do usuário', async () => {
			mockPrismaService.refreshToken.updateMany.mockResolvedValue({
				count: 3,
			});

			const result = await service.logoutAll('user-123');

			expect(result.message).toContain('todas as sessões');
			expect(
				mockPrismaService.refreshToken.updateMany,
			).toHaveBeenCalledWith({
				where: { userId: 'user-123', isRevoked: false },
				data: { isRevoked: true },
			});
		});
	});
});
