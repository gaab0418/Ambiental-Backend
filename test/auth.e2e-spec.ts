import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication, ValidationPipe } from '@nestjs/common';
import request from 'supertest';
import { AppModule } from '../src/app.module';
import { PrismaService } from '../src/shared/prisma/prisma.service';

describe('AuthController (e2e)', () => {
	let app: INestApplication;
	let prisma: PrismaService;

	// Dados de teste
	const testUser = {
		email: `test-${Date.now()}@example.com`,
		password: 'SecurePass@123',
		name: 'Test User',
	};

	let accessToken: string;
	let refreshToken: string;

	beforeAll(async () => {
		const moduleFixture: TestingModule = await Test.createTestingModule({
			imports: [AppModule],
		}).compile();

		app = moduleFixture.createNestApplication();
		app.useGlobalPipes(
			new ValidationPipe({
				whitelist: true,
				forbidNonWhitelisted: true,
				transform: true,
			}),
		);
		app.setGlobalPrefix('api/v1');

		await app.init();

		prisma = app.get(PrismaService);
	});

	afterAll(async () => {
		// Limpar dados de teste
		await prisma.refreshToken.deleteMany({
			where: { user: { email: testUser.email } },
		});
		await prisma.user.deleteMany({
			where: { email: testUser.email },
		});
		await app.close();
	});

	// ==================== REGISTRO ====================

	describe('POST /api/v1/auth/register', () => {
		it('deve registrar um novo usuário com sucesso', async () => {
			const response = await request(app.getHttpServer())
				.post('/api/v1/auth/register')
				.send(testUser)
				.expect(201);

			expect(response.body).toHaveProperty('access_token');
			expect(response.body).toHaveProperty('refresh_token');
			expect(response.body).toHaveProperty('user');
			expect(response.body.user.email).toBe(testUser.email);
			expect(response.body.user.name).toBe(testUser.name);
			expect(response.body.user).not.toHaveProperty('password');

			// Salvar tokens para testes subsequentes
			accessToken = response.body.access_token;
			refreshToken = response.body.refresh_token;
		});

		it('deve retornar 409 ao registrar email duplicado', async () => {
			const response = await request(app.getHttpServer())
				.post('/api/v1/auth/register')
				.send(testUser)
				.expect(409);

			expect(response.body.message).toContain('Email já está em uso');
		});

		it('deve retornar 400 com email inválido', async () => {
			await request(app.getHttpServer())
				.post('/api/v1/auth/register')
				.send({
					email: 'email-invalido',
					password: 'SecurePass@123',
					name: 'Test',
				})
				.expect(400);
		});

		it('deve retornar 400 com senha fraca', async () => {
			await request(app.getHttpServer())
				.post('/api/v1/auth/register')
				.send({
					email: 'outro@example.com',
					password: '123', // senha muito curta
					name: 'Test',
				})
				.expect(400);
		});
	});

	// ==================== LOGIN ====================

	describe('POST /api/v1/auth/login', () => {
		it('deve fazer login com sucesso', async () => {
			const response = await request(app.getHttpServer())
				.post('/api/v1/auth/login')
				.send({
					email: testUser.email,
					password: testUser.password,
				})
				.expect(200);

			expect(response.body).toHaveProperty('access_token');
			expect(response.body).toHaveProperty('refresh_token');
			expect(response.body).toHaveProperty('user');
			expect(response.body.user.email).toBe(testUser.email);

			// Atualizar tokens
			accessToken = response.body.access_token;
			refreshToken = response.body.refresh_token;
		});

		it('deve retornar 401 com senha incorreta', async () => {
			await request(app.getHttpServer())
				.post('/api/v1/auth/login')
				.send({
					email: testUser.email,
					password: 'senha-errada',
				})
				.expect(401);
		});

		it('deve retornar 401 com email não cadastrado', async () => {
			await request(app.getHttpServer())
				.post('/api/v1/auth/login')
				.send({
					email: 'naoexiste@example.com',
					password: 'qualquer',
				})
				.expect(401);
		});
	});

	// ==================== ROTA PROTEGIDA (/me) ====================

	describe('GET /api/v1/auth/me', () => {
		it('deve retornar dados do usuário autenticado', async () => {
			const response = await request(app.getHttpServer())
				.get('/api/v1/auth/me')
				.set('Authorization', `Bearer ${accessToken}`)
				.expect(200);

			expect(response.body.email).toBe(testUser.email);
			expect(response.body.name).toBe(testUser.name);
			expect(response.body).not.toHaveProperty('password');
		});

		it('deve retornar 401 sem token', async () => {
			await request(app.getHttpServer())
				.get('/api/v1/auth/me')
				.expect(401);
		});

		it('deve retornar 401 com token inválido', async () => {
			await request(app.getHttpServer())
				.get('/api/v1/auth/me')
				.set('Authorization', 'Bearer token-invalido')
				.expect(401);
		});
	});

	// ==================== REFRESH TOKEN ====================

	describe('POST /api/v1/auth/refresh', () => {
		it('deve renovar tokens com sucesso', async () => {
			const response = await request(app.getHttpServer())
				.post('/api/v1/auth/refresh')
				.send({ refreshToken })
				.expect(200);

			expect(response.body).toHaveProperty('access_token');
			expect(response.body).toHaveProperty('refresh_token');
			expect(response.body.refresh_token).not.toBe(refreshToken); // Rotação

			// Salvar novo refresh token
			const oldRefreshToken = refreshToken;
			refreshToken = response.body.refresh_token;
			accessToken = response.body.access_token;

			// Verificar que token antigo foi revogado
			await request(app.getHttpServer())
				.post('/api/v1/auth/refresh')
				.send({ refreshToken: oldRefreshToken })
				.expect(401);
		});

		it('deve retornar 401 com refresh token inválido', async () => {
			await request(app.getHttpServer())
				.post('/api/v1/auth/refresh')
				.send({ refreshToken: 'token-invalido' })
				.expect(401);
		});

		it('deve retornar 400 sem refresh token', async () => {
			await request(app.getHttpServer())
				.post('/api/v1/auth/refresh')
				.send({})
				.expect(400);
		});
	});

	// ==================== LOGOUT ====================

	describe('POST /api/v1/auth/logout', () => {
		it('deve fazer logout com sucesso', async () => {
			const response = await request(app.getHttpServer())
				.post('/api/v1/auth/logout')
				.send({ refreshToken })
				.expect(200);

			expect(response.body.message).toContain('Logout');
		});

		it('refresh token deve estar invalidado após logout', async () => {
			await request(app.getHttpServer())
				.post('/api/v1/auth/refresh')
				.send({ refreshToken })
				.expect(401);
		});
	});

	// ==================== LOGOUT ALL ====================

	describe('POST /api/v1/auth/logout-all', () => {
		beforeAll(async () => {
			// Fazer login novamente para ter tokens válidos
			const response = await request(app.getHttpServer())
				.post('/api/v1/auth/login')
				.send({
					email: testUser.email,
					password: testUser.password,
				});
			accessToken = response.body.access_token;
			refreshToken = response.body.refresh_token;
		});

		it('deve invalidar todas as sessões', async () => {
			const response = await request(app.getHttpServer())
				.post('/api/v1/auth/logout-all')
				.set('Authorization', `Bearer ${accessToken}`)
				.expect(200);

			expect(response.body.message).toContain('todas as sessões');
		});

		it('deve retornar 401 sem autenticação', async () => {
			await request(app.getHttpServer())
				.post('/api/v1/auth/logout-all')
				.expect(401);
		});
	});
});
