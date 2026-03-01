import {
	Controller,
	Get,
	Post,
	Delete,
	Param,
	Req,
	UseGuards,
	HttpCode,
	HttpStatus,
	BadRequestException,
} from '@nestjs/common';
import {
	ApiTags,
	ApiBearerAuth,
	ApiSecurity,
	ApiResponse,
	ApiNotFoundResponse,
	ApiForbiddenResponse,
	ApiConsumes,
	ApiBody,
} from '@nestjs/swagger';
import { FastifyRequest } from 'fastify';
import { ChatUploadService } from './chat-upload.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { LicenseGuard } from '../license/license.guard';
import { CurrentUser } from '../auth/decorators/current-user.decorator';
import type { User } from '@prisma/client';

@Controller('chats/:chatId/attachments')
@ApiTags('Chat - Uploads')
@ApiBearerAuth('JWT-auth')
@ApiSecurity('OAuth2-login')
@UseGuards(LicenseGuard, JwtAuthGuard)
export class ChatUploadController {
	constructor(private readonly chatUploadService: ChatUploadService) {}

	@Post()
	@ApiConsumes('multipart/form-data')
	@ApiBody({
		schema: {
			type: 'object',
			properties: {
				file: {
					type: 'string',
					format: 'binary',
					description: 'Arquivo para upload',
				},
			},
			required: ['file'],
		},
	})
	@ApiResponse({
		status: 201,
		description: 'Arquivo anexado com sucesso',
	})
	@ApiNotFoundResponse({ description: 'Chat não encontrado' })
	@ApiForbiddenResponse({ description: 'Acesso negado ao chat' })
	async upload(
		@Param('chatId') chatId: string,
		@CurrentUser() user: User,
		@Req() req: FastifyRequest,
	) {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		const data = await (req as any).file();

		if (!data) {
			throw new BadRequestException('Nenhum arquivo enviado');
		}

		const buffer = await data.toBuffer();

		return this.chatUploadService.upload(chatId, user.id, {
			buffer,
			originalname: data.filename,
			mimetype: data.mimetype,
			size: buffer.length,
		});
	}

	@Get()
	@ApiResponse({
		status: 200,
		description: 'Lista de arquivos do chat',
	})
	@ApiNotFoundResponse({ description: 'Chat não encontrado' })
	@ApiForbiddenResponse({ description: 'Acesso negado ao chat' })
	async findAll(@Param('chatId') chatId: string, @CurrentUser() user: User) {
		return this.chatUploadService.findAllByChat(chatId, user.id);
	}

	@Delete(':id')
	@HttpCode(HttpStatus.OK)
	@ApiResponse({
		status: 200,
		description: 'Arquivo removido (soft delete)',
	})
	@ApiNotFoundResponse({ description: 'Arquivo não encontrado' })
	@ApiForbiddenResponse({ description: 'Acesso negado' })
	async remove(
		@Param('chatId') chatId: string,
		@Param('id') id: string,
		@CurrentUser() user: User,
	) {
		return this.chatUploadService.remove(id, chatId, user.id);
	}
}
