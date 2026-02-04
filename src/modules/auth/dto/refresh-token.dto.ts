import { IsNotEmpty, IsString } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class RefreshTokenDto {
	@ApiProperty({
		description: 'Refresh token do usuário',
		example: 'eyJhJ9yJd9a11f2....',
		required: true,
	})
	@IsString({ message: 'Refresh token deve ser uma string' })
	@IsNotEmpty({ message: 'Refresh token é obrigatório' })
	refreshToken: string;
}
