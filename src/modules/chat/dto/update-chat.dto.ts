import { IsString, MaxLength } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class UpdateChatDto {
	@ApiProperty({ description: 'Novo título da conversa', maxLength: 255 })
	@IsString()
	@MaxLength(255)
	title: string;
}
