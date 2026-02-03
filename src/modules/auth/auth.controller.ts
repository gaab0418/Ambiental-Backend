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

@Controller('auth')
export class AuthController {
	constructor(private readonly authService: AuthService) {}

	@Post('register')
	async register(@Body() dto: RegisterDto) {
		return this.authService.register(dto);
	}

	@UseGuards(LocalAuthGuard)
	@Post('login')
	@HttpCode(HttpStatus.OK)
	async login(@CurrentUser() user: User, @Body() _dto: LoginDto) {
		return this.authService.login(user);
	}

	@Post('refresh')
	@HttpCode(HttpStatus.OK)
	async refresh(@Body() dto: RefreshTokenDto) {
		return this.authService.refreshTokens(dto.refreshToken);
	}

	@Post('logout')
	@HttpCode(HttpStatus.OK)
	async logout(@Body() dto: RefreshTokenDto) {
		return this.authService.logout(dto.refreshToken);
	}

	@UseGuards(JwtAuthGuard)
	@Post('logout-all')
	@HttpCode(HttpStatus.OK)
	async logoutAll(@CurrentUser() user: User) {
		return this.authService.logoutAll(user.id);
	}

	@UseGuards(JwtAuthGuard)
	@Get('me')
	async me(@CurrentUser() user: User) {
		const { password, ...sanitized } = user;
		return sanitized;
	}
}
