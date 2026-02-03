import { Injectable, UnauthorizedException } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { ConfigService } from '@nestjs/config';
import { UsersService } from '../../users/users.service';

export interface JwtPayload {
	sub: string;
	email: string;
}

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
	constructor(
		configService: ConfigService,
		private readonly usersService: UsersService,
	) {
		const secret = configService.get<string>('JWT_SECRET');
		if (!secret) {
			throw new Error(
				'JWT_SECRET não está definido nas variáveis de ambiente',
			);
		}
		super({
			jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
			ignoreExpiration: false,
			secretOrKey: secret,
		});
	}

	async validate(payload: JwtPayload) {
		const user = await this.usersService.findById(payload.sub);
		if (!user) {
			throw new UnauthorizedException('Usuário não encontrado');
		} else if (!user.isActive) {
			throw new UnauthorizedException('Usuário inativo');
		}
		return user;
	}
}
