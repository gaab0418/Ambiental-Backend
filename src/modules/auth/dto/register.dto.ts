import {
	IsEmail,
	IsNotEmpty,
	IsString,
	MinLength,
	IsOptional,
} from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class RegisterDto {
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
	@MinLength(6, { message: 'Senha deve ter no mínimo 6 caracteres' })
	password: string;

	@ApiProperty({
		description: 'Nome do usuário',
		example: 'John Doe',
		required: false,
	})
	@IsString({ message: 'Nome deve ser uma string' })
	@IsOptional()
	name?: string;
}
