import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app.module';
import {
	FastifyAdapter,
	NestFastifyApplication,
} from '@nestjs/platform-fastify';
import { ConfigService } from '@nestjs/config';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';

async function bootstrap() {
	const app = await NestFactory.create<NestFastifyApplication>(
		AppModule,
		new FastifyAdapter(),
	);

	const config = new DocumentBuilder()
		.setTitle('Ambiental API')
		.setDescription('Ambiental API - Master')
		.setVersion('1.0')
		.addTag('Ambiental')
		.addBearerAuth()
		.build();

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

	app.useGlobalPipes(
		new ValidationPipe({
			whitelist: true,
			forbidNonWhitelisted: true,
			transform: true,
		}),
	);

	const document = SwaggerModule.createDocument(app, config);
	SwaggerModule.setup('api/v1/docs', app, document, {
		jsonDocumentUrl: 'api/v1/docs/json',
		swaggerOptions: {
			url: 'api/v1/docs/json',
		},
	});

	const port = configService.get<number>('SERVER_PORT', 3000);
	await app.listen(port, '0.0.0.0');
}
bootstrap();
