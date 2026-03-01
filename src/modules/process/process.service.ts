import {
	Injectable,
	NotFoundException,
	ForbiddenException,
	Logger,
} from '@nestjs/common';
import { PrismaService } from '../../shared/prisma/prisma.service';
import { Prisma } from '@prisma/client';
import { CreateProcessDto } from './dto/create-process.dto';
import { UpdateProcessDto } from './dto/update-process.dto';

@Injectable()
export class ProcessService {
	private readonly logger = new Logger(ProcessService.name);

	constructor(private readonly prisma: PrismaService) {}

	async create(userId: string, dto: CreateProcessDto) {
		const process = await this.prisma.process.create({
			data: {
				title: dto.title,
				description: dto.description,
				userId,
			},
		});

		this.logger.log(`Processo criado: ${process.id} por usuário ${userId}`);
		return process;
	}

	async findAllByUser(userId: string) {
		return this.prisma.process.findMany({
			where: {
				userId,
				deletedAt: null,
			},
			include: {
				checklists: {
					orderBy: { order: 'asc' },
				},
				_count: {
					select: { chats: true },
				},
			},
			orderBy: { createdAt: 'desc' },
		});
	}

	async findOne(id: string, userId: string) {
		const process = await this.prisma.process.findUnique({
			where: { id },
			include: {
				checklists: {
					orderBy: { order: 'asc' },
				},
				_count: {
					select: { chats: true, attachments: true },
				},
			},
		});

		if (!process || process.deletedAt) {
			throw new NotFoundException('Processo não encontrado');
		}

		if (process.userId !== userId) {
			throw new ForbiddenException('Acesso negado a este processo');
		}

		return process;
	}

	async update(id: string, userId: string, dto: UpdateProcessDto) {
		await this.findOne(id, userId);

		const updated = await this.prisma.process.update({
			where: { id },
			data: {
				...(dto.title !== undefined && { title: dto.title }),
				...(dto.description !== undefined && {
					description: dto.description,
				}),
				...(dto.status !== undefined && { status: dto.status }),
				...(dto.currentStep !== undefined && {
					currentStep: dto.currentStep,
				}),
				...(dto.metadata !== undefined && {
					metadata: dto.metadata as unknown as Prisma.InputJsonValue,
				}),
			},
			include: {
				checklists: {
					orderBy: { order: 'asc' },
				},
			},
		});

		this.logger.log(`Processo atualizado: ${id} por usuário ${userId}`);
		return updated;
	}

	async remove(id: string, userId: string) {
		await this.findOne(id, userId);

		await this.prisma.process.update({
			where: { id },
			data: { deletedAt: new Date() },
		});

		this.logger.log(
			`Processo removido (soft delete): ${id} por usuário ${userId}`,
		);
		return { message: 'Processo removido com sucesso' };
	}
}
