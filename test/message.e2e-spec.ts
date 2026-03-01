import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication, ValidationPipe } from '@nestjs/common';
import request from 'supertest';
import { AppModule } from '../src/app.module';
import { PrismaService } from '../src/shared/prisma/prisma.service';

describe('MessageController (e2e)', () => {
	let app: INestApplication;
	let prisma: PrismaService;

	// Dados de teste
	const testUser = {
		email: `msg-test-${Date.now()}@example.com`,
		password: 'SecurePass@123',
		name: 'Message Test User',
	};

	const secondUser = {
		email: `msg-test2-${Date.now()}@example.com`,
		password: 'SecurePass@456',
		name: 'Second User',
	};

	let accessToken: string;
	let secondAccessToken: string;
	let chatId: string;
	let messageId: string;

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

		// Registrar primeiro usuário
		const registerRes = await request(app.getHttpServer())
			.post('/api/v1/auth/register')
			.send(testUser)
			.expect(201);

		accessToken = registerRes.body.access_token;

		// Registrar segundo usuário
		const registerRes2 = await request(app.getHttpServer())
			.post('/api/v1/auth/register')
			.send(secondUser)
			.expect(201);

		secondAccessToken = registerRes2.body.access_token;

		// Criar chat para os testes
		const chatRes = await request(app.getHttpServer())
			.post('/api/v1/chats')
			.set('Authorization', `Bearer ${accessToken}`)
			.send({ title: 'Chat de teste para mensagens' })
			.expect(201);

		chatId = chatRes.body.id;
	});

	afterAll(async () => {
		// Limpar dados de teste na ordem correta (dependências)
		await prisma.message.deleteMany({
			where: { chat: { id: chatId } },
		});
		await prisma.chat.deleteMany({
			where: { id: chatId },
		});
		await prisma.refreshToken.deleteMany({
			where: {
				user: {
					email: { in: [testUser.email, secondUser.email] },
				},
			},
		});
		await prisma.user.deleteMany({
			where: {
				email: { in: [testUser.email, secondUser.email] },
			},
		});
		await app.close();
	});

	// ==================== CRIAR MENSAGEM ====================

	describe('POST /api/v1/chats/:chatId/messages', () => {
		it('deve criar mensagem com sucesso', async () => {
			const response = await request(app.getHttpServer())
				.post(`/api/v1/chats/${chatId}/messages`)
				.set('Authorization', `Bearer ${accessToken}`)
				.send({ content: 'Primeira mensagem de teste' })
				.expect(201);

			expect(response.body).toHaveProperty('id');
			expect(response.body.content).toBe('Primeira mensagem de teste');
			expect(response.body.role).toBe('USER');
			expect(response.body.chatId).toBe(chatId);

			messageId = response.body.id;
		});

		it('deve criar segunda mensagem no mesmo chat', async () => {
			const response = await request(app.getHttpServer())
				.post(`/api/v1/chats/${chatId}/messages`)
				.set('Authorization', `Bearer ${accessToken}`)
				.send({ content: 'Segunda mensagem de teste' })
				.expect(201);

			expect(response.body.content).toBe('Segunda mensagem de teste');
		});

		it('deve retornar 400 com body vazio', async () => {
			await request(app.getHttpServer())
				.post(`/api/v1/chats/${chatId}/messages`)
				.set('Authorization', `Bearer ${accessToken}`)
				.send({})
				.expect(400);
		});

		it('deve retornar 400 com content vazio', async () => {
			await request(app.getHttpServer())
				.post(`/api/v1/chats/${chatId}/messages`)
				.set('Authorization', `Bearer ${accessToken}`)
				.send({ content: '' })
				.expect(400);
		});

		it('deve retornar 401 sem autenticação', async () => {
			await request(app.getHttpServer())
				.post(`/api/v1/chats/${chatId}/messages`)
				.send({ content: 'Sem auth' })
				.expect(401);
		});

		it('deve negar acesso a chat de outro usuário', async () => {
			await request(app.getHttpServer())
				.post(`/api/v1/chats/${chatId}/messages`)
				.set('Authorization', `Bearer ${secondAccessToken}`)
				.send({ content: 'Acesso indevido' })
				.expect(403);
		});

		it('deve retornar 404 para chat inexistente', async () => {
			const fakeChatId = '00000000-0000-0000-0000-000000000000';
			await request(app.getHttpServer())
				.post(`/api/v1/chats/${fakeChatId}/messages`)
				.set('Authorization', `Bearer ${accessToken}`)
				.send({ content: 'Chat inexistente' })
				.expect(404);
		});
	});

	// ==================== LISTAR MENSAGENS ====================

	describe('GET /api/v1/chats/:chatId/messages', () => {
		it('deve listar mensagens do chat do usuário logado', async () => {
			const response = await request(app.getHttpServer())
				.get(`/api/v1/chats/${chatId}/messages`)
				.set('Authorization', `Bearer ${accessToken}`)
				.expect(200);

			expect(Array.isArray(response.body)).toBeTruthy();
			expect(response.body.length).toBeGreaterThanOrEqual(2);

			// Verifica que todas são do chat correto
			for (const msg of response.body) {
				expect(msg.chatId).toBe(chatId);
				expect(msg.deletedAt).toBeNull();
			}
		});

		it('deve retornar mensagens ordenadas por createdAt ascendente', async () => {
			const response = await request(app.getHttpServer())
				.get(`/api/v1/chats/${chatId}/messages`)
				.set('Authorization', `Bearer ${accessToken}`)
				.expect(200);

			for (let i = 1; i < response.body.length; i++) {
				const prevDate = new Date(response.body[i - 1].createdAt);
				const currDate = new Date(response.body[i].createdAt);
				expect(currDate.getTime()).toBeGreaterThanOrEqual(
					prevDate.getTime(),
				);
			}
		});

		it('deve retornar 401 sem autenticação', async () => {
			await request(app.getHttpServer())
				.get(`/api/v1/chats/${chatId}/messages`)
				.expect(401);
		});

		it('deve negar acesso a mensagens de chat de outro usuário', async () => {
			await request(app.getHttpServer())
				.get(`/api/v1/chats/${chatId}/messages`)
				.set('Authorization', `Bearer ${secondAccessToken}`)
				.expect(403);
		});

		it('deve retornar 404 para chat inexistente', async () => {
			const fakeChatId = '00000000-0000-0000-0000-000000000000';
			await request(app.getHttpServer())
				.get(`/api/v1/chats/${fakeChatId}/messages`)
				.set('Authorization', `Bearer ${accessToken}`)
				.expect(404);
		});
	});

	// ==================== EDITAR MENSAGEM ====================

	describe('PATCH /api/v1/chats/:chatId/messages/:id', () => {
		it('deve editar mensagem do próprio usuário', async () => {
			const response = await request(app.getHttpServer())
				.patch(`/api/v1/chats/${chatId}/messages/${messageId}`)
				.set('Authorization', `Bearer ${accessToken}`)
				.send({ content: 'Mensagem editada' })
				.expect(200);

			expect(response.body.content).toBe('Mensagem editada');
			expect(response.body.id).toBe(messageId);
		});

		it('deve retornar 400 com content vazio', async () => {
			await request(app.getHttpServer())
				.patch(`/api/v1/chats/${chatId}/messages/${messageId}`)
				.set('Authorization', `Bearer ${accessToken}`)
				.send({ content: '' })
				.expect(400);
		});

		it('deve retornar 401 sem autenticação', async () => {
			await request(app.getHttpServer())
				.patch(`/api/v1/chats/${chatId}/messages/${messageId}`)
				.send({ content: 'Sem auth' })
				.expect(401);
		});

		it('deve negar acesso a mensagem de chat de outro usuário', async () => {
			await request(app.getHttpServer())
				.patch(`/api/v1/chats/${chatId}/messages/${messageId}`)
				.set('Authorization', `Bearer ${secondAccessToken}`)
				.send({ content: 'Acesso indevido' })
				.expect(403);
		});

		it('deve retornar 404 para mensagem inexistente', async () => {
			const fakeId = '00000000-0000-0000-0000-000000000000';
			await request(app.getHttpServer())
				.patch(`/api/v1/chats/${chatId}/messages/${fakeId}`)
				.set('Authorization', `Bearer ${accessToken}`)
				.send({ content: 'Inexistente' })
				.expect(404);
		});
	});

	// ==================== REMOVER MENSAGEM (soft delete) ====================

	describe('DELETE /api/v1/chats/:chatId/messages/:id', () => {
		it('deve retornar 401 sem autenticação', async () => {
			await request(app.getHttpServer())
				.delete(`/api/v1/chats/${chatId}/messages/${messageId}`)
				.expect(401);
		});

		it('deve negar acesso a mensagem de chat de outro usuário', async () => {
			await request(app.getHttpServer())
				.delete(`/api/v1/chats/${chatId}/messages/${messageId}`)
				.set('Authorization', `Bearer ${secondAccessToken}`)
				.expect(403);
		});

		it('deve fazer soft delete da mensagem', async () => {
			const response = await request(app.getHttpServer())
				.delete(`/api/v1/chats/${chatId}/messages/${messageId}`)
				.set('Authorization', `Bearer ${accessToken}`)
				.expect(200);

			expect(response.body.message).toContain('removida');
		});

		it('mensagem deletada não deve aparecer na listagem', async () => {
			const response = await request(app.getHttpServer())
				.get(`/api/v1/chats/${chatId}/messages`)
				.set('Authorization', `Bearer ${accessToken}`)
				.expect(200);

			const deletedMsg = response.body.find(
				(m: any) => m.id === messageId,
			);
			expect(deletedMsg).toBeUndefined();
		});

		it('deve retornar 404 ao tentar deletar mensagem já deletada', async () => {
			await request(app.getHttpServer())
				.delete(`/api/v1/chats/${chatId}/messages/${messageId}`)
				.set('Authorization', `Bearer ${accessToken}`)
				.expect(404);
		});

		it('deve retornar 404 para mensagem inexistente', async () => {
			const fakeId = '00000000-0000-0000-0000-000000000000';
			await request(app.getHttpServer())
				.delete(`/api/v1/chats/${chatId}/messages/${fakeId}`)
				.set('Authorization', `Bearer ${accessToken}`)
				.expect(404);
		});
	});
});
