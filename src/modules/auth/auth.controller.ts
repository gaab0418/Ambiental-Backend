import {
	Controller,
	Post,
	Get,
	Body,
	UseGuards,
	HttpCode,
	HttpStatus,
	UnauthorizedException,
} from '@nestjs/common';
import { AuthService } from './auth.service';
import { RegisterDto } from './dto/register.dto';
import { LoginDto } from './dto/login.dto';
import { RefreshTokenDto } from './dto/refresh-token.dto';
import { LocalAuthGuard } from './guards/local-auth.guard';
import { JwtAuthGuard } from './guards/jwt-auth.guard';
import { CurrentUser } from './decorators/current-user.decorator';
import type { User } from '@prisma/client';
import {
	ApiResponse,
	ApiUnauthorizedResponse,
	ApiConflictResponse,
	ApiSecurity,
	ApiBearerAuth,
} from '@nestjs/swagger';

@Controller('auth')
export class AuthController {
	constructor(private readonly authService: AuthService) {}

	@ApiResponse({ status: 201, description: 'Usuário registrado com sucesso' })
	@ApiConflictResponse({ description: 'Email já está em uso' })
	@Post('register')
	async register(@Body() dto: RegisterDto) {
		return this.authService.register(dto);
	}

	@ApiResponse({ status: 200, description: 'Login realizado com sucesso' })
	@ApiUnauthorizedResponse({
		description: 'Email não encontrado/Senha inválida/Usuário está inativo',
	})
	@UseGuards(LocalAuthGuard)
	@Post('login')
	@HttpCode(HttpStatus.OK)
	async login(@CurrentUser() user: User, @Body() _dto: LoginDto) {
		return this.authService.login(user);
	}

	/**
	 * Endpoint especial para o OAuth2 password flow do Swagger UI.
	 * Recebe username/password como form-data e retorna access_token no formato OAuth2.
	 */
	@ApiResponse({ status: 200, description: 'Login via Swagger OAuth2' })
	@ApiUnauthorizedResponse({ description: 'Credenciais inválidas' })
	@Post('swagger-login')
	@HttpCode(HttpStatus.OK)
	async swaggerLogin(
		@Body()
		body: {
			username: string;
			password: string;
			grant_type?: string;
		},
	) {
		const user = await this.authService.validateUser(
			body.username,
			body.password,
		);
		if (!user) {
			throw new UnauthorizedException('Credenciais inválidas');
		}
		const tokens = await this.authService.login(user);
		return {
			access_token: tokens.access_token,
			token_type: 'bearer',
			refresh_token: tokens.refresh_token,
		};
	}

	@ApiResponse({
		status: 200,
		description: 'Refresh token realizado com sucesso',
	})
	@ApiUnauthorizedResponse({
		description: 'Refresh token inválido/revogado/expirado/inativo',
	})
	@Post('refresh')
	@HttpCode(HttpStatus.OK)
	async refresh(@Body() dto: RefreshTokenDto) {
		return this.authService.refreshTokens(dto.refreshToken);
	}

	@ApiResponse({ status: 200, description: 'Logout realizado com sucesso' })
	@Post('logout')
	@HttpCode(HttpStatus.OK)
	async logout(@Body() dto: RefreshTokenDto) {
		return this.authService.logout(dto.refreshToken);
	}

	@ApiBearerAuth('JWT-auth')
	@ApiSecurity('OAuth2-login')
	@ApiResponse({ status: 200, description: 'Logout realizado com sucesso' })
	@UseGuards(JwtAuthGuard)
	@Post('logout-all')
	@HttpCode(HttpStatus.OK)
	async logoutAll(@CurrentUser() user: User) {
		return this.authService.logoutAll(user.id);
	}

	@ApiResponse({ status: 200, description: 'Informações do usuário atual' })
	@ApiUnauthorizedResponse({
		description: 'Token JWT inválido/revogado/expirado',
	})
	@ApiBearerAuth('JWT-auth')
	@ApiSecurity('OAuth2-login')
	@UseGuards(JwtAuthGuard)
	@Get('me')
	async me(@CurrentUser() user: User) {
		const { password, ...sanitized } = user;
		return sanitized;
	}
}
