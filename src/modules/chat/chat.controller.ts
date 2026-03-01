import {
	Controller,
	Get,
	Post,
	Patch,
	Delete,
	Body,
	Param,
	Query,
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
	ApiQuery,
} from '@nestjs/swagger';
import { ChatService } from './chat.service';
import { CreateChatDto } from './dto/create-chat.dto';
import { UpdateChatDto } from './dto/update-chat.dto';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { LicenseGuard } from '../license/license.guard';
import { CurrentUser } from '../auth/decorators/current-user.decorator';
import type { User } from '@prisma/client';

@Controller('chats')
@ApiTags('Chat')
@ApiBearerAuth('JWT-auth')
@ApiSecurity('OAuth2-login')
@UseGuards(LicenseGuard, JwtAuthGuard)
export class ChatController {
	constructor(private readonly chatService: ChatService) {}

	@Post()
	@ApiResponse({ status: 201, description: 'Chat criado com sucesso' })
	async create(@CurrentUser() user: User, @Body() dto: CreateChatDto) {
		return this.chatService.create(user.id, dto);
	}

	@Get()
	@ApiResponse({
		status: 200,
		description: 'Lista de chats do usuário',
	})
	@ApiQuery({
		name: 'includeArchived',
		required: false,
		type: Boolean,
		description: 'Incluir chats arquivados',
	})
	async findAll(
		@CurrentUser() user: User,
		@Query('includeArchived') includeArchived?: string,
	) {
		return this.chatService.findAllByUser(
			user.id,
			includeArchived === 'true',
		);
	}

	@Get(':id')
	@ApiResponse({ status: 200, description: 'Detalhes do chat' })
	@ApiNotFoundResponse({ description: 'Chat não encontrado' })
	@ApiForbiddenResponse({ description: 'Acesso negado' })
	async findOne(@Param('id') id: string, @CurrentUser() user: User) {
		return this.chatService.findOne(id, user.id);
	}

	@Patch(':id')
	@ApiResponse({
		status: 200,
		description: 'Título do chat atualizado',
	})
	@ApiNotFoundResponse({ description: 'Chat não encontrado' })
	@ApiForbiddenResponse({ description: 'Acesso negado' })
	async update(
		@Param('id') id: string,
		@CurrentUser() user: User,
		@Body() dto: UpdateChatDto,
	) {
		return this.chatService.update(id, user.id, dto);
	}

	@Patch(':id/archive')
	@ApiResponse({
		status: 200,
		description: 'Chat arquivado/desarquivado',
	})
	@ApiNotFoundResponse({ description: 'Chat não encontrado' })
	@ApiForbiddenResponse({ description: 'Acesso negado' })
	async archive(@Param('id') id: string, @CurrentUser() user: User) {
		return this.chatService.archive(id, user.id);
	}

	@Delete(':id')
	@HttpCode(HttpStatus.OK)
	@ApiResponse({
		status: 200,
		description: 'Chat removido (soft delete)',
	})
	@ApiNotFoundResponse({ description: 'Chat não encontrado' })
	@ApiForbiddenResponse({ description: 'Acesso negado' })
	async remove(@Param('id') id: string, @CurrentUser() user: User) {
		return this.chatService.remove(id, user.id);
	}
}
