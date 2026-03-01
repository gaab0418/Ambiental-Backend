import {
	Controller,
	Get,
	Post,
	Patch,
	Delete,
	Body,
	Param,
	UseGuards,
	HttpCode,
	HttpStatus,
} from '@nestjs/common';
import {
	ApiTags,
	ApiBearerAuth,
	ApiSecurity,
	ApiResponse,
	ApiNotFoundResponse,
	ApiForbiddenResponse,
} from '@nestjs/swagger';
import { MessageService } from './message.service';
import { CreateMessageDto } from './dto/create-message.dto';
import { UpdateMessageDto } from './dto/update-message.dto';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { LicenseGuard } from '../license/license.guard';
import { CurrentUser } from '../auth/decorators/current-user.decorator';
import type { User } from '@prisma/client';

@Controller('chats/:chatId/messages')
@ApiTags('Mensagens')
@ApiBearerAuth('JWT-auth')
@ApiSecurity('OAuth2-login')
@UseGuards(LicenseGuard, JwtAuthGuard)
export class MessageController {
	constructor(private readonly messageService: MessageService) {}

	@Post()
	@ApiResponse({
		status: 201,
		description: 'Mensagem enviada com sucesso',
	})
	@ApiNotFoundResponse({ description: 'Chat não encontrado' })
	@ApiForbiddenResponse({ description: 'Acesso negado ao chat' })
	async create(
		@Param('chatId') chatId: string,
		@CurrentUser() user: User,
		@Body() dto: CreateMessageDto,
	) {
		return this.messageService.create(chatId, user.id, dto);
	}

	@Get()
	@ApiResponse({
		status: 200,
		description: 'Lista de mensagens do chat',
	})
	@ApiNotFoundResponse({ description: 'Chat não encontrado' })
	@ApiForbiddenResponse({ description: 'Acesso negado ao chat' })
	async findAll(@Param('chatId') chatId: string, @CurrentUser() user: User) {
		return this.messageService.findAllByChat(chatId, user.id);
	}

	@Patch(':id')
	@ApiResponse({
		status: 200,
		description: 'Mensagem editada com sucesso',
	})
	@ApiNotFoundResponse({ description: 'Mensagem não encontrada' })
	@ApiForbiddenResponse({
		description: 'Acesso negado / Apenas mensagens do usuário',
	})
	async update(
		@Param('chatId') chatId: string,
		@Param('id') id: string,
		@CurrentUser() user: User,
		@Body() dto: UpdateMessageDto,
	) {
		return this.messageService.update(id, chatId, user.id, dto);
	}

	@Delete(':id')
	@HttpCode(HttpStatus.OK)
	@ApiResponse({
		status: 200,
		description: 'Mensagem removida (soft delete)',
	})
	@ApiNotFoundResponse({ description: 'Mensagem não encontrada' })
	@ApiForbiddenResponse({ description: 'Acesso negado' })
	async remove(
		@Param('chatId') chatId: string,
		@Param('id') id: string,
		@CurrentUser() user: User,
	) {
		return this.messageService.remove(id, chatId, user.id);
	}
}
