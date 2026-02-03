import {
	IsEmail,
	IsNotEmpty,
	IsOptional,
	IsString,
	MinLength,
} from 'class-validator';

export class CreateUserDto {
	@IsEmail({}, { message: 'Email deve ser um endereço válido' })
	@IsNotEmpty({ message: 'Email é obrigatório' })
	email: string;

	@IsString({ message: 'Nome deve ser uma string' })
	@IsOptional()
	name?: string;

	@IsString({ message: 'Senha deve ser uma string' })
	@IsNotEmpty({ message: 'Senha é obrigatória' })
	@MinLength(6, { message: 'Senha deve ter no mínimo 6 caracteres' })
	password: string;
}
