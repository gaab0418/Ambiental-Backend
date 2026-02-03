import { Test, TestingModule } from '@nestjs/testing';
import { UsersService } from './users.service';
import { PrismaService } from '../../shared/prisma/prisma.service';

// Mock do PrismaService
const mockPrismaService = {
	user: {
		findUnique: jest.fn(),
		create: jest.fn(),
	},
};

describe('UsersService', () => {
	let service: UsersService;

	const mockUser = {
		id: 'user-123',
		email: 'test@example.com',
		password: 'hashed-password',
		name: 'Test User',
		role: 'USER' as const,
		isActive: true,
		createdAt: new Date(),
		updatedAt: new Date(),
	};

	beforeEach(async () => {
		const module: TestingModule = await Test.createTestingModule({
			providers: [
				UsersService,
				{ provide: PrismaService, useValue: mockPrismaService },
			],
		}).compile();

		service = module.get<UsersService>(UsersService);

		// Resetar mocks
		jest.clearAllMocks();
	});

	it('deve estar definido', () => {
		expect(service).toBeDefined();
	});

	// ==================== findByEmail ====================

	describe('findByEmail', () => {
		it('deve retornar usuário quando encontrado', async () => {
			mockPrismaService.user.findUnique.mockResolvedValue(mockUser);

			const result = await service.findByEmail('test@example.com');

			expect(result).toBeDefined();
			expect(result?.email).toBe('test@example.com');
			expect(mockPrismaService.user.findUnique).toHaveBeenCalledWith({
				where: { email: 'test@example.com' },
			});
		});

		it('deve retornar null quando usuário não encontrado', async () => {
			mockPrismaService.user.findUnique.mockResolvedValue(null);

			const result = await service.findByEmail('naoexiste@example.com');

			expect(result).toBeNull();
		});
	});

	// ==================== findById ====================

	describe('findById', () => {
		it('deve retornar usuário quando encontrado', async () => {
			mockPrismaService.user.findUnique.mockResolvedValue(mockUser);

			const result = await service.findById('user-123');

			expect(result).toBeDefined();
			expect(result?.id).toBe('user-123');
			expect(mockPrismaService.user.findUnique).toHaveBeenCalledWith({
				where: { id: 'user-123' },
			});
		});

		it('deve retornar null quando usuário não encontrado', async () => {
			mockPrismaService.user.findUnique.mockResolvedValue(null);

			const result = await service.findById('id-inexistente');

			expect(result).toBeNull();
		});
	});

	// ==================== create ====================

	describe('create', () => {
		const createUserDto = {
			email: 'novo@example.com',
			password: 'hashed-password',
			name: 'Novo User',
		};

		it('deve criar usuário com sucesso', async () => {
			const createdUser = { ...mockUser, ...createUserDto, id: 'new-id' };
			mockPrismaService.user.create.mockResolvedValue(createdUser);

			const result = await service.create(createUserDto);

			expect(result).toBeDefined();
			expect(result.email).toBe(createUserDto.email);
			expect(result.name).toBe(createUserDto.name);
			expect(mockPrismaService.user.create).toHaveBeenCalledWith({
				data: createUserDto,
			});
		});

		it('deve criar usuário sem nome (opcional)', async () => {
			const dtoSemNome = {
				email: 'semnome@example.com',
				password: 'hashed-password',
			};
			const createdUser = { ...mockUser, ...dtoSemNome, name: null };
			mockPrismaService.user.create.mockResolvedValue(createdUser);

			const result = await service.create(dtoSemNome);

			expect(result).toBeDefined();
			expect(result.email).toBe(dtoSemNome.email);
			expect(result.name).toBeNull();
		});

		it('deve lançar erro ao falhar na criação', async () => {
			mockPrismaService.user.create.mockRejectedValue(
				new Error('Database error'),
			);

			await expect(service.create(createUserDto)).rejects.toThrow(
				'Database error',
			);
		});
	});
});
