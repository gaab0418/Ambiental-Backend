import {
	Injectable,
	NotFoundException,
	ForbiddenException,
	Logger,
} from '@nestjs/common';
import { PrismaService } from '../../shared/prisma/prisma.service';
import { ChatService } from '../chat/chat.service';
import { CreateMessageDto } from './dto/create-message.dto';
import { UpdateMessageDto } from './dto/update-message.dto';

@Injectable()
export class MessageService {
	private readonly logger = new Logger(MessageService.name);

	constructor(
		private readonly prisma: PrismaService,
		private readonly chatService: ChatService,
	) {}

	async create(chatId: string, userId: string, dto: CreateMessageDto) {
		// Valida ownership do chat
		await this.chatService.validateOwnership(chatId, userId);

		const message = await this.prisma.message.create({
			data: {
				content: dto.content,
				role: 'USER',
				chatId,
				userId,
			},
		});

		// Atualiza updatedAt do chat
		await this.prisma.chat.update({
			where: { id: chatId },
			data: { updatedAt: new Date() },
		});

		this.logger.log(
			`Mensagem criada: ${message.id} no chat ${chatId} por usuário ${userId}`,
		);
		return message;
	}

	async findAllByChat(chatId: string, userId: string) {
		// Valida ownership do chat
		await this.chatService.validateOwnership(chatId, userId);

		return this.prisma.message.findMany({
			where: {
				chatId,
				deletedAt: null,
			},
			orderBy: { createdAt: 'asc' },
		});
	}

	async update(
		id: string,
		chatId: string,
		userId: string,
		dto: UpdateMessageDto,
	) {
		await this.chatService.validateOwnership(chatId, userId);

		const message = await this.prisma.message.findUnique({
			where: { id },
		});

		if (!message || message.deletedAt || message.chatId !== chatId) {
			throw new NotFoundException('Mensagem não encontrada');
		}

		// Apenas mensagens do role USER podem ser editadas
		if (message.role !== 'USER') {
			throw new ForbiddenException(
				'Apenas mensagens do usuário podem ser editadas',
			);
		}

		if (message.userId !== userId) {
			throw new ForbiddenException('Acesso negado a esta mensagem');
		}

		const updated = await this.prisma.message.update({
			where: { id },
			data: { content: dto.content },
		});

		this.logger.log(
			`Mensagem editada: ${id} no chat ${chatId} por usuário ${userId}`,
		);
		return updated;
	}

	async remove(id: string, chatId: string, userId: string) {
		await this.chatService.validateOwnership(chatId, userId);

		const message = await this.prisma.message.findUnique({
			where: { id },
		});

		if (!message || message.deletedAt || message.chatId !== chatId) {
			throw new NotFoundException('Mensagem não encontrada');
		}

		if (message.userId !== userId && message.role === 'USER') {
			throw new ForbiddenException('Acesso negado a esta mensagem');
		}

		await this.prisma.message.update({
			where: { id },
			data: { deletedAt: new Date() },
		});

		this.logger.log(
			`Mensagem removida (soft delete): ${id} no chat ${chatId} por usuário ${userId}`,
		);
		return { message: 'Mensagem removida com sucesso' };
	}
}
