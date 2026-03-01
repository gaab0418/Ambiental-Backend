import { IsString, IsNotEmpty } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class UpdateMessageDto {
	@ApiProperty({ description: 'Novo conteúdo da mensagem' })
	@IsString()
	@IsNotEmpty()
	content: string;
}
