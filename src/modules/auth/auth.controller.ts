import {
	Controller,
	Post,
	Get,
	Body,
	UseGuards,
	HttpCode,
	HttpStatus,
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
	@UseGuards(JwtAuthGuard)
	@Get('me')
	async me(@CurrentUser() user: User) {
		const { password, ...sanitized } = user;
		return sanitized;
	}
}
