import {
	Injectable,
	NotFoundException,
	ForbiddenException,
	Logger,
} from '@nestjs/common';
import { PrismaService } from '../../shared/prisma/prisma.service';
import { StorageService } from '../../shared/storage/storage.service';
import { ChatService } from '../chat/chat.service';

@Injectable()
export class ChatUploadService {
	private readonly logger = new Logger(ChatUploadService.name);

	constructor(
		private readonly prisma: PrismaService,
		private readonly storageService: StorageService,
		private readonly chatService: ChatService,
	) {}

	async upload(
		chatId: string,
		userId: string,
		file: {
			buffer: Buffer;
			originalname: string;
			mimetype: string;
			size: number;
		},
	) {
		// Valida ownership do chat
		const chat = await this.chatService.validateOwnership(chatId, userId);

		// Salva arquivo no storage (subdiretório por chat)
		const storagePath = await this.storageService.save(
			file.buffer,
			file.originalname,
			`chats/${chatId}`,
		);

		const attachment = await this.prisma.chatAttachment.create({
			data: {
				originalName: file.originalname,
				storagePath,
				mimeType: file.mimetype,
				sizeBytes: file.size,
				chatId,
				processId: chat.processId,
				uploadedById: userId,
			},
		});

		this.logger.log(
			`Arquivo anexado: ${file.originalname} ao chat ${chatId} por usuário ${userId}`,
		);
		return attachment;
	}

	async findAllByChat(chatId: string, userId: string) {
		await this.chatService.validateOwnership(chatId, userId);

		return this.prisma.chatAttachment.findMany({
			where: {
				chatId,
				deletedAt: null,
			},
			orderBy: { createdAt: 'desc' },
		});
	}

	async remove(id: string, chatId: string, userId: string) {
		await this.chatService.validateOwnership(chatId, userId);

		const attachment = await this.prisma.chatAttachment.findUnique({
			where: { id },
		});

		if (
			!attachment ||
			attachment.deletedAt ||
			attachment.chatId !== chatId
		) {
			throw new NotFoundException('Arquivo não encontrado');
		}

		if (attachment.uploadedById !== userId) {
			throw new ForbiddenException('Acesso negado a este arquivo');
		}

		// Soft delete — arquivo físico é MANTIDO (política de persistência)
		await this.prisma.chatAttachment.update({
			where: { id },
			data: { deletedAt: new Date() },
		});

		this.logger.log(
			`Arquivo removido (soft delete): ${id} do chat ${chatId} por usuário ${userId}`,
		);
		return { message: 'Arquivo removido com sucesso' };
	}
}
