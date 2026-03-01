import { IsString, IsOptional, MaxLength, IsUUID } from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class CreateChatDto {
	@ApiProperty({ description: 'Título da conversa', maxLength: 255 })
	@IsString()
	@MaxLength(255)
	title: string;

	@ApiPropertyOptional({
		description: 'ID do processo vinculado (opcional)',
	})
	@IsOptional()
	@IsUUID()
	processId?: string;
}
