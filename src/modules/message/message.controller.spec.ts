import { Test, TestingModule } from '@nestjs/testing';
import { MessageController } from './message.controller';
import { MessageService } from './message.service';
import { ForbiddenException, NotFoundException } from '@nestjs/common';
import { LicenseGuard } from '../license/license.guard';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import type { User } from '@prisma/client';

// ─── Mocks ───────────────────────────────────────────────────────────────────
const mockMessageService = {
	create: jest.fn(),
	findAllByChat: jest.fn(),
	update: jest.fn(),
	remove: jest.fn(),
};

// Guards mockados para evitar dependências complexas no teste unitário
const mockLicenseGuard = { canActivate: jest.fn().mockReturnValue(true) };
const mockJwtAuthGuard = { canActivate: jest.fn().mockReturnValue(true) };

describe('MessageController', () => {
	let controller: MessageController;

	const mockUser: User = {
		id: 'user-123',
		email: 'test@example.com',
		name: 'Test User',
		password: 'hashed-password',
		role: 'USER',
		isActive: true,
		createdAt: new Date(),
		updatedAt: new Date(),
	};

	const mockChatId = 'chat-456';

	const mockMessages = [
		{
			id: 'msg-001',
			content: 'Primeira mensagem',
			role: 'USER',
			chatId: mockChatId,
			userId: mockUser.id,
			createdAt: new Date('2026-03-01T10:00:00Z'),
			updatedAt: new Date('2026-03-01T10:00:00Z'),
			deletedAt: null,
		},
		{
			id: 'msg-002',
			content: 'Resposta do assistente',
			role: 'ASSISTANT',
			chatId: mockChatId,
			userId: null,
			createdAt: new Date('2026-03-01T10:01:00Z'),
			updatedAt: new Date('2026-03-01T10:01:00Z'),
			deletedAt: null,
		},
	];

	beforeEach(async () => {
		const module: TestingModule = await Test.createTestingModule({
			controllers: [MessageController],
			providers: [
				{ provide: MessageService, useValue: mockMessageService },
			],
		})
			.overrideGuard(LicenseGuard)
			.useValue(mockLicenseGuard)
			.overrideGuard(JwtAuthGuard)
			.useValue(mockJwtAuthGuard)
			.compile();

		controller = module.get<MessageController>(MessageController);

		jest.clearAllMocks();
	});

	// ==================== CREATE ====================

	describe('create', () => {
		it('deve criar mensagem chamando o service com parâmetros corretos', async () => {
			mockMessageService.create.mockResolvedValue(mockMessages[0]);

			const result = await controller.create(mockChatId, mockUser, {
				content: 'Primeira mensagem',
			});

			expect(result).toEqual(mockMessages[0]);
			expect(mockMessageService.create).toHaveBeenCalledWith(
				mockChatId,
				mockUser.id,
				{ content: 'Primeira mensagem' },
			);
		});
	});

	// ==================== FIND ALL (GET /chats/:chatId/messages) ====================

	describe('findAll', () => {
		it('deve listar mensagens chamando o service com chatId e userId corretos', async () => {
			mockMessageService.findAllByChat.mockResolvedValue(mockMessages);

			const result = await controller.findAll(mockChatId, mockUser);

			expect(result).toEqual(mockMessages);
			expect(result).toHaveLength(2);
			expect(mockMessageService.findAllByChat).toHaveBeenCalledWith(
				mockChatId,
				mockUser.id,
			);
		});

		it('deve retornar array vazio quando não há mensagens', async () => {
			mockMessageService.findAllByChat.mockResolvedValue([]);

			const result = await controller.findAll(mockChatId, mockUser);

			expect(result).toEqual([]);
			expect(result).toHaveLength(0);
		});

		it('deve propagar NotFoundException quando chat não existe', async () => {
			mockMessageService.findAllByChat.mockRejectedValue(
				new NotFoundException('Chat não encontrado'),
			);

			await expect(
				controller.findAll('chat-inexistente', mockUser),
			).rejects.toThrow(NotFoundException);
		});

		it('deve propagar ForbiddenException quando chat não pertence ao usuário', async () => {
			mockMessageService.findAllByChat.mockRejectedValue(
				new ForbiddenException('Acesso negado a este chat'),
			);

			await expect(
				controller.findAll(mockChatId, mockUser),
			).rejects.toThrow(ForbiddenException);
		});
	});

	// ==================== UPDATE ====================

	describe('update', () => {
		it('deve editar mensagem chamando o service com parâmetros corretos', async () => {
			const updated = { ...mockMessages[0], content: 'Editada' };
			mockMessageService.update.mockResolvedValue(updated);

			const result = await controller.update(
				mockChatId,
				'msg-001',
				mockUser,
				{ content: 'Editada' },
			);

			expect(result.content).toBe('Editada');
			expect(mockMessageService.update).toHaveBeenCalledWith(
				'msg-001',
				mockChatId,
				mockUser.id,
				{ content: 'Editada' },
			);
		});
	});

	// ==================== REMOVE ====================

	describe('remove', () => {
		it('deve remover mensagem chamando o service com parâmetros corretos', async () => {
			mockMessageService.remove.mockResolvedValue({
				message: 'Mensagem removida com sucesso',
			});

			const result = await controller.remove(
				mockChatId,
				'msg-001',
				mockUser,
			);

			expect(result.message).toBe('Mensagem removida com sucesso');
			expect(mockMessageService.remove).toHaveBeenCalledWith(
				'msg-001',
				mockChatId,
				mockUser.id,
			);
		});
	});
});
