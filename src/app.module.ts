import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { ScheduleModule } from '@nestjs/schedule';
import { PrismaModule } from './shared/prisma/prisma.module';
import { StorageModule } from './shared/storage/storage.module';
import { UsersModule } from './modules/users/users.module';
import { AuthModule } from './modules/auth/auth.module';
import { LicenseModule } from './modules/license/license.module';
import { ProcessModule } from './modules/process/process.module';
import { ChatModule } from './modules/chat/chat.module';
import { MessageModule } from './modules/message/message.module';
import { ChatUploadModule } from './modules/chat-upload/chat-upload.module';
import { LoggerModule } from 'nestjs-pino';
import { AppController } from './app.controller';
import { AppService } from './app.service';

@Module({
	imports: [
		ConfigModule.forRoot({
			isGlobal: true,
			envFilePath: '.env',
		}),
		ScheduleModule.forRoot(),
		LoggerModule.forRoot({
			pinoHttp: {
				redact: {
					paths: [
						'req.headers.authorization',
						'req.body.password',
						'req.body.token',
						'req.body.refreshToken',
					],
				},
				transport: {
					targets: [
						{
							target: 'pino-pretty',
							level:
								process.env.NODE_ENV === 'production'
									? 'info'
									: 'debug',
							options: { colorize: true, singleLine: true },
						},
						{
							target: 'pino-loki',
							level: 'info',
							options: {
								batching: true,
								interval: 5,
								host:
									process.env.LOKI_HOST ||
									'http://localhost:3101',
								labels: {
									job: 'nestjs-backend',
									app: 'ambiental-api',
									env: process.env.NODE_ENV || 'development',
								},
								propsToLabels: ['level'],
							},
						},
					],
				},
				genReqId: (req) =>
					req.headers['x-request-id'] || crypto.randomUUID(),
			},
		}),
		PrismaModule,
		StorageModule,
		UsersModule,
		AuthModule,
		LicenseModule,
		ProcessModule,
		ChatModule,
		MessageModule,
		ChatUploadModule,
	],
	controllers: [AppController],
	providers: [AppService],
})
export class AppModule {}
