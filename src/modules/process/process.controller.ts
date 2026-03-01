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
import { ProcessService } from './process.service';
import { CreateProcessDto } from './dto/create-process.dto';
import { UpdateProcessDto } from './dto/update-process.dto';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import { LicenseGuard } from '../license/license.guard';
import { CurrentUser } from '../auth/decorators/current-user.decorator';
import type { User } from '@prisma/client';

@Controller('processes')
@ApiTags('Processos')
@ApiBearerAuth('JWT-auth')
@ApiSecurity('OAuth2-login')
@UseGuards(LicenseGuard, JwtAuthGuard)
export class ProcessController {
	constructor(private readonly processService: ProcessService) {}

	@Post()
	@ApiResponse({
		status: 201,
		description: 'Processo criado com sucesso',
	})
	async create(@CurrentUser() user: User, @Body() dto: CreateProcessDto) {
		return this.processService.create(user.id, dto);
	}

	@Get()
	@ApiResponse({
		status: 200,
		description: 'Lista de processos do usuário',
	})
	async findAll(@CurrentUser() user: User) {
		return this.processService.findAllByUser(user.id);
	}

	@Get(':id')
	@ApiResponse({ status: 200, description: 'Detalhes do processo' })
	@ApiNotFoundResponse({ description: 'Processo não encontrado' })
	@ApiForbiddenResponse({ description: 'Acesso negado' })
	async findOne(@Param('id') id: string, @CurrentUser() user: User) {
		return this.processService.findOne(id, user.id);
	}

	@Patch(':id')
	@ApiResponse({
		status: 200,
		description: 'Processo atualizado com sucesso',
	})
	@ApiNotFoundResponse({ description: 'Processo não encontrado' })
	@ApiForbiddenResponse({ description: 'Acesso negado' })
	async update(
		@Param('id') id: string,
		@CurrentUser() user: User,
		@Body() dto: UpdateProcessDto,
	) {
		return this.processService.update(id, user.id, dto);
	}

	@Delete(':id')
	@HttpCode(HttpStatus.OK)
	@ApiResponse({
		status: 200,
		description: 'Processo removido com sucesso (soft delete)',
	})
	@ApiNotFoundResponse({ description: 'Processo não encontrado' })
	@ApiForbiddenResponse({ description: 'Acesso negado' })
	async remove(@Param('id') id: string, @CurrentUser() user: User) {
		return this.processService.remove(id, user.id);
	}
}
