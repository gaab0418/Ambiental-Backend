import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { AuthService } from './auth.service';
import { AuthController } from './auth.controller';
import { UsersModule } from '../users/users.module';
import { LocalStrategy } from './strategies/local.strategy';
import { JwtStrategy } from './strategies/jwt.strategy';

@Module({
	imports: [
		UsersModule,
		PassportModule,
		JwtModule.registerAsync({
			imports: [ConfigModule],
			inject: [ConfigService],
			useFactory: (configService: ConfigService) => {
				const secret = configService.get<string>('JWT_SECRET');
				const expiration = configService.get<string>(
					'JWT_ACCESS_EXPIRATION',
					'15m',
				);

				// Converte string como "15m" para segundos
				const parseExpiration = (exp: string): number => {
					const match = exp.match(/^(\d+)([smhd])$/);
					if (!match) return 900; // 15 min padrão
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
				};

				return {
					secret,
					signOptions: {
						expiresIn: parseExpiration(expiration),
					},
				};
			},
		}),
	],
	controllers: [AuthController],
	providers: [AuthService, LocalStrategy, JwtStrategy],
	exports: [AuthService],
})
export class AuthModule {}
