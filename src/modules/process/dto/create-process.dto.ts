import { IsString, IsOptional, MaxLength } from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class CreateProcessDto {
	@ApiProperty({ description: 'Título do processo', maxLength: 255 })
	@IsString()
	@MaxLength(255)
	title: string;

	@ApiPropertyOptional({ description: 'Descrição breve do processo' })
	@IsOptional()
	@IsString()
	@MaxLength(1000)
	description?: string;
}
