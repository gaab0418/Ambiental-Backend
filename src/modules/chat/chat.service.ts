import {
	Injectable,
	NotFoundException,
	ForbiddenException,
	Logger,
} from '@nestjs/common';
import { PrismaService } from '../../shared/prisma/prisma.service';
import { CreateChatDto } from './dto/create-chat.dto';
import { UpdateChatDto } from './dto/update-chat.dto';

@Injectable()
export class ChatService {
	private readonly logger = new Logger(ChatService.name);

	constructor(private readonly prisma: PrismaService) {}

	async create(userId: string, dto: CreateChatDto) {
		// Se processId informado, validar ownership
		if (dto.processId) {
			const process = await this.prisma.process.findUnique({
				where: { id: dto.processId },
			});

			if (!process || process.deletedAt || process.userId !== userId) {
				throw new NotFoundException('Processo não encontrado');
			}
		}

		const chat = await this.prisma.chat.create({
			data: {
				title: dto.title,
				userId,
				processId: dto.processId,
			},
		});

		this.logger.log(`Chat criado: ${chat.id} por usuário ${userId}`);
		return chat;
	}

	async findAllByUser(userId: string, includeArchived: boolean = false) {
		return this.prisma.chat.findMany({
			where: {
				userId,
				deletedAt: null,
				...(includeArchived ? {} : { isArchived: false }),
			},
			include: {
				process: {
					select: { id: true, title: true, status: true },
				},
				_count: {
					select: { messages: true, attachments: true },
				},
			},
			orderBy: { updatedAt: 'desc' },
		});
	}

	async findOne(id: string, userId: string) {
		const chat = await this.prisma.chat.findUnique({
			where: { id },
			include: {
				process: {
					select: { id: true, title: true, status: true },
				},
				_count: {
					select: { messages: true, attachments: true },
				},
			},
		});

		if (!chat || chat.deletedAt) {
			throw new NotFoundException('Chat não encontrado');
		}

		if (chat.userId !== userId) {
			throw new ForbiddenException('Acesso negado a este chat');
		}

		return chat;
	}

	/**
	 * Valida que o chat pertence ao usuário (uso interno por outros módulos).
	 */
	async validateOwnership(chatId: string, userId: string) {
		return this.findOne(chatId, userId);
	}

	async update(id: string, userId: string, dto: UpdateChatDto) {
		await this.findOne(id, userId);

		const updated = await this.prisma.chat.update({
			where: { id },
			data: { title: dto.title },
		});

		this.logger.log(`Chat atualizado: ${id} por usuário ${userId}`);
		return updated;
	}

	async archive(id: string, userId: string) {
		const chat = await this.findOne(id, userId);

		const updated = await this.prisma.chat.update({
			where: { id },
			data: { isArchived: !chat.isArchived },
		});

		const action = updated.isArchived ? 'arquivado' : 'desarquivado';
		this.logger.log(`Chat ${action}: ${id} por usuário ${userId}`);
		return updated;
	}

	async remove(id: string, userId: string) {
		await this.findOne(id, userId);

		await this.prisma.chat.update({
			where: { id },
			data: { deletedAt: new Date() },
		});

		this.logger.log(
			`Chat removido (soft delete): ${id} por usuário ${userId}`,
		);
		return { message: 'Chat removido com sucesso' };
	}
}
