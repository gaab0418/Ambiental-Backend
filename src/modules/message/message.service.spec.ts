import { Test, TestingModule } from '@nestjs/testing';
import { MessageService } from './message.service';
import { PrismaService } from '../../shared/prisma/prisma.service';
import { ChatService } from '../chat/chat.service';
import { NotFoundException, ForbiddenException } from '@nestjs/common';

// ─── Mocks ───────────────────────────────────────────────────────────────────
const mockPrismaService = {
	message: {
		create: jest.fn(),
		findMany: jest.fn(),
		findUnique: jest.fn(),
		update: jest.fn(),
	},
	chat: {
		update: jest.fn(),
	},
};

const mockChatService = {
	validateOwnership: jest.fn(),
};

describe('MessageService', () => {
	let service: MessageService;

	const mockUserId = 'user-123';
	const mockChatId = 'chat-456';

	const mockMessage = {
		id: 'msg-789',
		content: 'Olá, preciso de ajuda com licenciamento',
		role: 'USER' as const,
		chatId: mockChatId,
		userId: mockUserId,
		createdAt: new Date('2026-03-01T10:00:00Z'),
		updatedAt: new Date('2026-03-01T10:00:00Z'),
		deletedAt: null,
	};

	const mockAssistantMessage = {
		id: 'msg-790',
		content: 'Claro, posso ajudar com o processo de licenciamento.',
		role: 'ASSISTANT' as const,
		chatId: mockChatId,
		userId: null,
		createdAt: new Date('2026-03-01T10:01:00Z'),
		updatedAt: new Date('2026-03-01T10:01:00Z'),
		deletedAt: null,
	};

	const mockDeletedMessage = {
		id: 'msg-791',
		content: 'Mensagem deletada',
		role: 'USER' as const,
		chatId: mockChatId,
		userId: mockUserId,
		createdAt: new Date('2026-03-01T09:00:00Z'),
		updatedAt: new Date('2026-03-01T09:00:00Z'),
		deletedAt: new Date('2026-03-01T09:30:00Z'),
	};

	beforeEach(async () => {
		const module: TestingModule = await Test.createTestingModule({
			providers: [
				MessageService,
				{ provide: PrismaService, useValue: mockPrismaService },
				{ provide: ChatService, useValue: mockChatService },
			],
		}).compile();

		service = module.get<MessageService>(MessageService);

		jest.clearAllMocks();
	});

	// ==================== CREATE ====================

	describe('create', () => {
		it('deve criar mensagem com sucesso e atualizar o chat', async () => {
			mockChatService.validateOwnership.mockResolvedValue({});
			mockPrismaService.message.create.mockResolvedValue(mockMessage);
			mockPrismaService.chat.update.mockResolvedValue({});

			const result = await service.create(mockChatId, mockUserId, {
				content: 'Olá, preciso de ajuda com licenciamento',
			});

			expect(result).toEqual(mockMessage);
			expect(mockChatService.validateOwnership).toHaveBeenCalledWith(
				mockChatId,
				mockUserId,
			);
			expect(mockPrismaService.message.create).toHaveBeenCalledWith({
				data: {
					content: 'Olá, preciso de ajuda com licenciamento',
					role: 'USER',
					chatId: mockChatId,
					userId: mockUserId,
				},
			});
			expect(mockPrismaService.chat.update).toHaveBeenCalledWith({
				where: { id: mockChatId },
				data: { updatedAt: expect.any(Date) },
			});
		});

		it('deve lançar erro quando chat não pertence ao usuário', async () => {
			mockChatService.validateOwnership.mockRejectedValue(
				new ForbiddenException('Acesso negado a este chat'),
			);

			await expect(
				service.create(mockChatId, 'outro-user', {
					content: 'Tentativa indevida',
				}),
			).rejects.toThrow(ForbiddenException);
		});

		it('deve lançar erro quando chat não existe', async () => {
			mockChatService.validateOwnership.mockRejectedValue(
				new NotFoundException('Chat não encontrado'),
			);

			await expect(
				service.create('chat-inexistente', mockUserId, {
					content: 'Teste',
				}),
			).rejects.toThrow(NotFoundException);
		});
	});

	// ==================== FIND ALL BY CHAT ====================

	describe('findAllByChat', () => {
		it('deve listar todas as mensagens não deletadas do chat ordenadas por createdAt asc', async () => {
			const messages = [mockMessage, mockAssistantMessage];
			mockChatService.validateOwnership.mockResolvedValue({});
			mockPrismaService.message.findMany.mockResolvedValue(messages);

			const result = await service.findAllByChat(mockChatId, mockUserId);

			expect(result).toEqual(messages);
			expect(result).toHaveLength(2);
			expect(mockChatService.validateOwnership).toHaveBeenCalledWith(
				mockChatId,
				mockUserId,
			);
			expect(mockPrismaService.message.findMany).toHaveBeenCalledWith({
				where: {
					chatId: mockChatId,
					deletedAt: null,
				},
				orderBy: { createdAt: 'asc' },
			});
		});

		it('não deve retornar mensagens com soft delete', async () => {
			// Simula que o Prisma filtra corretamente — só retorna a não deletada
			mockChatService.validateOwnership.mockResolvedValue({});
			mockPrismaService.message.findMany.mockResolvedValue([mockMessage]);

			const result = await service.findAllByChat(mockChatId, mockUserId);

			expect(result).toHaveLength(1);
			expect(result[0].deletedAt).toBeNull();
		});

		it('deve retornar array vazio quando o chat não tem mensagens', async () => {
			mockChatService.validateOwnership.mockResolvedValue({});
			mockPrismaService.message.findMany.mockResolvedValue([]);

			const result = await service.findAllByChat(mockChatId, mockUserId);

			expect(result).toEqual([]);
			expect(result).toHaveLength(0);
		});

		it('deve lançar ForbiddenException quando chat não pertence ao usuário', async () => {
			mockChatService.validateOwnership.mockRejectedValue(
				new ForbiddenException('Acesso negado a este chat'),
			);

			await expect(
				service.findAllByChat(mockChatId, 'outro-user'),
			).rejects.toThrow(ForbiddenException);

			expect(mockPrismaService.message.findMany).not.toHaveBeenCalled();
		});

		it('deve lançar NotFoundException quando chat não existe', async () => {
			mockChatService.validateOwnership.mockRejectedValue(
				new NotFoundException('Chat não encontrado'),
			);

			await expect(
				service.findAllByChat('chat-inexistente', mockUserId),
			).rejects.toThrow(NotFoundException);

			expect(mockPrismaService.message.findMany).not.toHaveBeenCalled();
		});
	});

	// ==================== UPDATE ====================

	describe('update', () => {
		it('deve editar mensagem do usuário com sucesso', async () => {
			const updatedMessage = {
				...mockMessage,
				content: 'Conteúdo atualizado',
			};
			mockChatService.validateOwnership.mockResolvedValue({});
			mockPrismaService.message.findUnique.mockResolvedValue(mockMessage);
			mockPrismaService.message.update.mockResolvedValue(updatedMessage);

			const result = await service.update(
				mockMessage.id,
				mockChatId,
				mockUserId,
				{ content: 'Conteúdo atualizado' },
			);

			expect(result.content).toBe('Conteúdo atualizado');
			expect(mockPrismaService.message.update).toHaveBeenCalledWith({
				where: { id: mockMessage.id },
				data: { content: 'Conteúdo atualizado' },
			});
		});

		it('deve lançar NotFoundException quando mensagem não existe', async () => {
			mockChatService.validateOwnership.mockResolvedValue({});
			mockPrismaService.message.findUnique.mockResolvedValue(null);

			await expect(
				service.update('msg-inexistente', mockChatId, mockUserId, {
					content: 'Teste',
				}),
			).rejects.toThrow(NotFoundException);
		});

		it('deve lançar NotFoundException quando mensagem está deletada (soft delete)', async () => {
			mockChatService.validateOwnership.mockResolvedValue({});
			mockPrismaService.message.findUnique.mockResolvedValue(
				mockDeletedMessage,
			);

			await expect(
				service.update(mockDeletedMessage.id, mockChatId, mockUserId, {
					content: 'Teste',
				}),
			).rejects.toThrow(NotFoundException);
		});

		it('deve lançar NotFoundException quando mensagem pertence a outro chat', async () => {
			const messageOutroChat = { ...mockMessage, chatId: 'outro-chat' };
			mockChatService.validateOwnership.mockResolvedValue({});
			mockPrismaService.message.findUnique.mockResolvedValue(
				messageOutroChat,
			);

			await expect(
				service.update(mockMessage.id, mockChatId, mockUserId, {
					content: 'Teste',
				}),
			).rejects.toThrow(NotFoundException);
		});

		it('deve lançar ForbiddenException ao tentar editar mensagem do ASSISTANT', async () => {
			mockChatService.validateOwnership.mockResolvedValue({});
			mockPrismaService.message.findUnique.mockResolvedValue(
				mockAssistantMessage,
			);

			await expect(
				service.update(
					mockAssistantMessage.id,
					mockChatId,
					mockUserId,
					{ content: 'Tentativa' },
				),
			).rejects.toThrow(ForbiddenException);
		});

		it('deve lançar ForbiddenException ao tentar editar mensagem de outro usuário', async () => {
			const messageOutroUser = { ...mockMessage, userId: 'outro-user' };
			mockChatService.validateOwnership.mockResolvedValue({});
			mockPrismaService.message.findUnique.mockResolvedValue(
				messageOutroUser,
			);

			await expect(
				service.update(mockMessage.id, mockChatId, mockUserId, {
					content: 'Tentativa',
				}),
			).rejects.toThrow(ForbiddenException);
		});
	});

	// ==================== REMOVE ====================

	describe('remove', () => {
		it('deve fazer soft delete da mensagem com sucesso', async () => {
			mockChatService.validateOwnership.mockResolvedValue({});
			mockPrismaService.message.findUnique.mockResolvedValue(mockMessage);
			mockPrismaService.message.update.mockResolvedValue({});

			const result = await service.remove(
				mockMessage.id,
				mockChatId,
				mockUserId,
			);

			expect(result.message).toBe('Mensagem removida com sucesso');
			expect(mockPrismaService.message.update).toHaveBeenCalledWith({
				where: { id: mockMessage.id },
				data: { deletedAt: expect.any(Date) },
			});
		});

		it('deve lançar NotFoundException quando mensagem não existe', async () => {
			mockChatService.validateOwnership.mockResolvedValue({});
			mockPrismaService.message.findUnique.mockResolvedValue(null);

			await expect(
				service.remove('msg-inexistente', mockChatId, mockUserId),
			).rejects.toThrow(NotFoundException);
		});

		it('deve lançar NotFoundException quando mensagem já está deletada', async () => {
			mockChatService.validateOwnership.mockResolvedValue({});
			mockPrismaService.message.findUnique.mockResolvedValue(
				mockDeletedMessage,
			);

			await expect(
				service.remove(mockDeletedMessage.id, mockChatId, mockUserId),
			).rejects.toThrow(NotFoundException);
		});

		it('deve lançar ForbiddenException ao tentar deletar mensagem USER de outro usuário', async () => {
			const messageOutroUser = { ...mockMessage, userId: 'outro-user' };
			mockChatService.validateOwnership.mockResolvedValue({});
			mockPrismaService.message.findUnique.mockResolvedValue(
				messageOutroUser,
			);

			await expect(
				service.remove(mockMessage.id, mockChatId, mockUserId),
			).rejects.toThrow(ForbiddenException);
		});

		it('deve permitir deletar mensagem ASSISTANT mesmo de outro usuário', async () => {
			mockChatService.validateOwnership.mockResolvedValue({});
			mockPrismaService.message.findUnique.mockResolvedValue(
				mockAssistantMessage,
			);
			mockPrismaService.message.update.mockResolvedValue({});

			const result = await service.remove(
				mockAssistantMessage.id,
				mockChatId,
				mockUserId,
			);

			expect(result.message).toBe('Mensagem removida com sucesso');
		});
	});
});
