import 'dotenv/config';
import { PrismaClient } from '@prisma/client';
import { PrismaPg } from '@prisma/adapter-pg';

const adapter = new PrismaPg({
	connectionString: process.env.DATABASE_URL,
});
const prisma = new PrismaClient({ adapter });

async function main() {
	console.log('Database Seeding...');

	// 1. Create Admin User (ID 1)
	const adminUser = await prisma.user.upsert({
		where: { email: 'admin@ambiental.local' },
		update: {
			role: 'ADMIN',
			isActive: true,
		},
		create: {
			email: 'admin@ambiental.local',
			name: 'Admin',
			password:
				'$2b$12$eTMY/pyy6ZAe8tnm0xVOk.PSllKnOFafgKaQroYarfEGosQefxFim', // admin123
			role: 'ADMIN',
			isActive: true,
		},
	});
	console.log('Admin User:', adminUser.email);

	console.log('Seed completed!');
}

main()
	.then(async () => {
		await prisma.$disconnect();
	})
	.catch(async (e) => {
		console.error(e);
		await prisma.$disconnect();
		process.exit(1);
	});
