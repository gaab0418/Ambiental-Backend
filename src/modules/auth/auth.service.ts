import {
	Injectable,
	ConflictException,
	UnauthorizedException,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';
import * as bcrypt from 'bcrypt';
import * as crypto from 'crypto';
import { UsersService } from '../users/users.service';
import { RegisterDto } from './dto/register.dto';
import { PrismaService } from '../../shared/prisma/prisma.service';
import type { User } from '@prisma/client';

@Injectable()
export class AuthService {
	private readonly pepper: string;
	private readonly accessTokenExpiration: number;
	private readonly refreshTokenExpirationDays: number;

	constructor(
		private readonly usersService: UsersService,
		private readonly jwtService: JwtService,
		private readonly configService: ConfigService,
		private readonly prisma: PrismaService,
	) {
		this.pepper = this.configService.get<string>('PASSWORD_PEPPER', '');
		this.accessTokenExpiration = this.parseExpiration(
			this.configService.get<string>('JWT_ACCESS_EXPIRATION', '15m'),
		);
		this.refreshTokenExpirationDays = this.parseExpirationToDays(
			this.configService.get<string>('JWT_REFRESH_EXPIRATION', '30d'),
		);
	}

	async validateUser(email: string, password: string): Promise<User | null> {
		const user = await this.usersService.findByEmail(email);
		if (!user) {
			throw new UnauthorizedException('Email não encontrado');
		}

		const isPasswordValid = await this.comparePasswords(
			password,
			user.password,
		);
		if (!isPasswordValid) {
			throw new UnauthorizedException('Senha inválida');
		}

		if (!user.isActive) {
			throw new UnauthorizedException('Usuário está inativo');
		}

		return user;
	}

	async login(user: User) {
		const accessToken = this.generateAccessToken(user);
		const refreshToken = await this.createRefreshToken(user.id);

		return {
			access_token: accessToken,
			refresh_token: refreshToken,
			user: this.sanitizeUser(user),
		};
	}

	async register(dto: RegisterDto) {
		const existingUser = await this.usersService.findByEmail(dto.email);
		if (existingUser) {
			throw new ConflictException('Email já está em uso');
		}

		const hashedPassword = await this.hashPassword(dto.password);

		const user = await this.usersService.create({
			email: dto.email,
			name: dto.name,
			password: hashedPassword,
		});

		const accessToken = this.generateAccessToken(user);
		const refreshToken = await this.createRefreshToken(user.id);

		return {
			access_token: accessToken,
			refresh_token: refreshToken,
			user: this.sanitizeUser(user),
		};
	}

	async refreshTokens(refreshTokenValue: string) {
		const storedToken = await this.prisma.refreshToken.findUnique({
			where: { token: refreshTokenValue },
			include: { user: true },
		});

		if (!storedToken) {
			throw new UnauthorizedException('Refresh token inválido');
		}

		if (storedToken.isRevoked) {
			throw new UnauthorizedException('Refresh token já foi revogado');
		}

		if (new Date() > storedToken.expiresAt) {
			throw new UnauthorizedException('Refresh token expirado');
		}

		if (!storedToken.user.isActive) {
			throw new UnauthorizedException('Usuário está inativo');
		}

		// Revogar token antigo (rotação de tokens)
		await this.prisma.refreshToken.update({
			where: { id: storedToken.id },
			data: { isRevoked: true },
		});

		// Gerar novos tokens
		const accessToken = this.generateAccessToken(storedToken.user);
		const newRefreshToken = await this.createRefreshToken(
			storedToken.userId,
		);

		return {
			access_token: accessToken,
			refresh_token: newRefreshToken,
			user: this.sanitizeUser(storedToken.user),
		};
	}

	async logout(refreshTokenValue: string) {
		const storedToken = await this.prisma.refreshToken.findUnique({
			where: { token: refreshTokenValue },
		});

		if (storedToken) {
			await this.prisma.refreshToken.update({
				where: { id: storedToken.id },
				data: { isRevoked: true },
			});
		}

		return { message: 'Logout realizado com sucesso' };
	}

	async logoutAll(userId: string) {
		await this.prisma.refreshToken.updateMany({
			where: { userId, isRevoked: false },
			data: { isRevoked: true },
		});

		return { message: 'Logout de todas as sessões realizado com sucesso' };
	}

	private generateAccessToken(user: User): string {
		const payload = { sub: user.id, email: user.email };
		return this.jwtService.sign(payload, {
			expiresIn: this.accessTokenExpiration,
		});
	}

	private async createRefreshToken(userId: string): Promise<string> {
		const token = crypto.randomBytes(64).toString('hex');
		const expiresAt = new Date();
		expiresAt.setDate(
			expiresAt.getDate() + this.refreshTokenExpirationDays,
		);

		await this.prisma.refreshToken.create({
			data: {
				token,
				userId,
				expiresAt,
			},
		});

		return token;
	}

	private async hashPassword(password: string): Promise<string> {
		const saltRounds = 12;
		const pepperedPassword = this.applyPepper(password);
		return bcrypt.hash(pepperedPassword, saltRounds);
	}

	private async comparePasswords(
		plainPassword: string,
		hashedPassword: string,
	): Promise<boolean> {
		const pepperedPassword = this.applyPepper(plainPassword);
		return bcrypt.compare(pepperedPassword, hashedPassword);
	}

	private applyPepper(password: string): string {
		return `${password}${this.pepper}`;
	}

	private parseExpiration(expiration: string): number {
		const match = expiration.match(/^(\d+)([smhd])$/);
		if (!match) return 900; // 15 min default
		const value = parseInt(match[1], 10);
		const unit = match[2];
		switch (unit) {
			case 's':
				return value;
			case 'm':
				return value * 60;
			case 'h':
				return value * 3600;
			case 'd':
				return value * 86400;
			default:
				return 900;
		}
	}

	private parseExpirationToDays(expiration: string): number {
		const match = expiration.match(/^(\d+)d$/);
		if (!match) return 30;
		return parseInt(match[1], 10);
	}

	private sanitizeUser(user: User) {
		// eslint-disable-next-line @typescript-eslint/no-unused-vars
		const { password, ...sanitized } = user;
		return sanitized;
	}
}
