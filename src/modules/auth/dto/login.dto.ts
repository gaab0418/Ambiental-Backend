import { IsEmail, IsNotEmpty, IsString } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class LoginDto {
	@ApiProperty({
		description: 'Email do usuário',
		example: 'example@example.com',
		required: true,
	})
	@IsEmail({}, { message: 'Email deve ser um endereço válido' })
	@IsNotEmpty({ message: 'Email é obrigatório' })
	email: string;

	@ApiProperty({
		description: 'Senha do usuário',
		example: '123456',
		required: true,
	})
	@IsString({ message: 'Senha deve ser uma string' })
	@IsNotEmpty({ message: 'Senha é obrigatória' })
	password: string;
}
