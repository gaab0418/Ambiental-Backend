import { IsString, IsNotEmpty } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class CreateMessageDto {
	@ApiProperty({ description: 'Conteúdo da mensagem' })
	@IsString()
	@IsNotEmpty()
	content: string;
}
