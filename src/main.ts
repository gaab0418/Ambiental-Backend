import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app.module';
import {
	FastifyAdapter,
	NestFastifyApplication,
} from '@nestjs/platform-fastify';
import { ConfigService } from '@nestjs/config';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { Logger } from 'nestjs-pino';
import { GLOBAL_PREFIX } from './shared/constants/constants';
import { execSync } from 'child_process';

// Forca UTF-8 no console do Windows para suportar acentos corretamente.
if (process.platform === 'win32') {
	try {
		execSync('chcp 65001', { stdio: 'ignore' });
	} catch {
		console.warn(
			'Nao foi possivel alterar o encoding do console para UTF-8',
		);
	}
}

async function bootstrap() {
	const app = await NestFactory.create<NestFastifyApplication>(
		AppModule,
		new FastifyAdapter(),
	);

	const config = new DocumentBuilder()
		.setTitle('Ambiental API - On-Premise Server')
		.setDescription('Ambiental API - On-Premise Server')
		.setVersion('1.0')
		.addBearerAuth(
			{
				type: 'http',
				scheme: 'bearer',
				bearerFormat: 'JWT',
				name: 'Authorization',
				description: 'Insira o token JWT manualmente',
				in: 'header',
			},
			'JWT-auth',
		)
		.addOAuth2(
			{
				type: 'oauth2',
				flows: {
					password: {
						tokenUrl: `auth/swagger-login`,
						scopes: {},
					},
				},
				description: 'Login com email e senha',
			},
			'OAuth2-login',
		)
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

	app.setGlobalPrefix(GLOBAL_PREFIX);
	app.useLogger(app.get(Logger));

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
