import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import {
	FastifyAdapter,
	NestFastifyApplication,
} from '@nestjs/platform-fastify';
import { ConfigService } from '@nestjs/config';

async function bootstrap() {
	const app = await NestFactory.create<NestFastifyApplication>(
		AppModule,
		new FastifyAdapter(),
	);

	const configService = app.get(ConfigService);
	const nodeEnv = configService.get<string>('NODE_ENV', 'development');

	if (nodeEnv !== 'production') {
		app.enableCors();
	} else {
		const allowedOrigins =
			configService.get<string>('ALLOWED_ORIGINS')?.split(',') || [];
		app.enableCors({
			origin: allowedOrigins,
			methods: 'GET,HEAD,PUT,PATCH,POST,DELETE,UPDATE',
			credentials: true,
		});
	}

	app.setGlobalPrefix('api/v1');

	const port = configService.get<number>('SERVER_PORT', 3000);
	await app.listen(port, '0.0.0.0');
}
bootstrap();
