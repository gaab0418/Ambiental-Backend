import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

@Injectable()
export class StorageService {
	private readonly logger = new Logger(StorageService.name);
	private readonly driver: string;
	private readonly localPath: string;

	constructor(private readonly configService: ConfigService) {
		this.driver = this.configService.get<string>('STORAGE_DRIVER', 'disk');
		this.localPath = this.configService.get<string>(
			'STORAGE_LOCAL_PATH',
			'./uploads',
		);

		if (this.driver === 'disk') {
			this.ensureDirectoryExists(this.localPath);
		}
	}

	/**
	 * Salva um arquivo no storage e retorna o caminho relativo.
	 */
	async save(
		file: Buffer,
		originalName: string,
		subDir?: string,
	): Promise<string> {
		if (this.driver === 'disk') {
			return this.saveToDisk(file, originalName, subDir);
		}

		// Futuro: driver s3
		throw new Error(`Storage driver "${this.driver}" não suportado`);
	}

	/**
	 * Retorna o caminho absoluto de um arquivo no storage.
	 */
	getAbsolutePath(storagePath: string): string {
		if (this.driver === 'disk') {
			return path.resolve(this.localPath, storagePath);
		}

		throw new Error(`Storage driver "${this.driver}" não suportado`);
	}

	/**
	 * Verifica se um arquivo existe no storage.
	 */
	async exists(storagePath: string): Promise<boolean> {
		if (this.driver === 'disk') {
			const fullPath = this.getAbsolutePath(storagePath);
			return fs.existsSync(fullPath);
		}

		throw new Error(`Storage driver "${this.driver}" não suportado`);
	}

	private async saveToDisk(
		file: Buffer,
		originalName: string,
		subDir?: string,
	): Promise<string> {
		const ext = path.extname(originalName);
		const uniqueName = `${crypto.randomUUID()}${ext}`;
		const relativePath = subDir
			? path.join(subDir, uniqueName)
			: uniqueName;
		const fullPath = path.resolve(this.localPath, relativePath);

		this.ensureDirectoryExists(path.dirname(fullPath));

		await fs.promises.writeFile(fullPath, file);
		this.logger.log(`Arquivo salvo: ${originalName} -> ${relativePath}`);

		return relativePath;
	}

	private ensureDirectoryExists(dirPath: string): void {
		if (!fs.existsSync(dirPath)) {
			fs.mkdirSync(dirPath, { recursive: true });
			this.logger.log(`Diretório criado: ${dirPath}`);
		}
	}
}
