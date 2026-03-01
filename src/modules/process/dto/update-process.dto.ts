import {
	IsString,
	IsOptional,
	MaxLength,
	IsEnum,
	IsInt,
	Min,
	IsObject,
} from 'class-validator';
import { ApiPropertyOptional } from '@nestjs/swagger';

enum ProcessStatusDto {
	DRAFT = 'DRAFT',
	IN_PROGRESS = 'IN_PROGRESS',
	COMPLETED = 'COMPLETED',
	ARCHIVED = 'ARCHIVED',
}

export class UpdateProcessDto {
	@ApiPropertyOptional({ description: 'Título do processo', maxLength: 255 })
	@IsOptional()
	@IsString()
	@MaxLength(255)
	title?: string;

	@ApiPropertyOptional({ description: 'Descrição breve do processo' })
	@IsOptional()
	@IsString()
	@MaxLength(1000)
	description?: string;

	@ApiPropertyOptional({
		description: 'Status do processo',
		enum: ProcessStatusDto,
	})
	@IsOptional()
	@IsEnum(ProcessStatusDto)
	status?: ProcessStatusDto;

	@ApiPropertyOptional({
		description: 'Etapa atual do checklist (0-indexed)',
	})
	@IsOptional()
	@IsInt()
	@Min(0)
	currentStep?: number;

	@ApiPropertyOptional({
		description: 'Metadados adicionais (JSONB)',
		type: 'object',
		additionalProperties: true,
	})
	@IsOptional()
	@IsObject()
	metadata?: Record<string, unknown>;
}
