import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { HttpService } from '@nestjs/axios';
import { Interval } from '@nestjs/schedule';
import { firstValueFrom, retry, timer } from 'rxjs';
import {
	LicenseCodes,
	LicenseStatus,
	LicenseValidationResponse,
} from './license.interfaces';

const DEFAULT_HEARTBEAT_MS = 5 * 60 * 1000; // 5 minutos
const DEFAULT_GRACE_PERIOD_HOURS = 24;
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 2000;

/**
 * Codes que representam situacoes irrecuperaveis — bloqueio imediato, sem grace period.
 */
const IMMEDIATE_BLOCK_CODES: ReadonlySet<LicenseCodes> = new Set([
	LicenseCodes.LICENSE_NOT_FOUND,
	LicenseCodes.LICENSE_DELETED,
	LicenseCodes.LICENSE_INACTIVE,
	LicenseCodes.LICENSE_ORGANIZATION_INACTIVE,
]);

/**
 * Codes que permitem grace period — o sistema continua funcionando
 * temporariamente ate que o problema seja resolvido.
 */
const GRACE_PERIOD_CODES: ReadonlySet<LicenseCodes> = new Set([
	LicenseCodes.LICENSE_SERVER_INACCESSIBLE,
	LicenseCodes.LICENSE_EXPIRED,
	LicenseCodes.LICENSE_SEATS_EXCEEDED,
]);

@Injectable()
export class LicenseService implements OnModuleInit {
	private readonly logger = new Logger(LicenseService.name);

	private status: LicenseStatus = {
		isValid: false,
		lastCheckedAt: new Date(0),
		code: LicenseCodes.LICENSE_TO_VALIDATE,
	};

	private readonly serverAddress: string;
	private readonly licenseKey: string;
	private readonly gracePeriodMs: number;
	private isConfigured = false;

	constructor(
		private readonly configService: ConfigService,
		private readonly httpService: HttpService,
	) {
		this.serverAddress =
			this.configService.get<string>('LICENSE_SERVER_ADDRESS') ?? '';

		this.licenseKey = this.configService.get<string>('LICENSE_KEY') ?? '';

		const gracePeriodHours = Number(
			this.configService.get<number>(
				'LICENSE_GRACE_PERIOD_HOURS',
				DEFAULT_GRACE_PERIOD_HOURS,
			),
		);
		this.gracePeriodMs = gracePeriodHours * 60 * 60 * 1000;
	}

	async onModuleInit(): Promise<void> {
		this.isConfigured = this.validateConfiguration();

		if (!this.isConfigured) {
			return;
		}

		this.logger.log(
			`Iniciando validacao de licenca contra ${this.serverAddress}`,
		);
		await this.validateLicense();
	}

	/**
	 * Valida as variaveis de ambiente obrigatorias para o modulo de licenca.
	 * Se alguma estiver ausente ou invalida, bloqueia o sistema imediatamente
	 * com code LICENSE_MISCONFIGURED e mensagem detalhada.
	 */
	private validateConfiguration(): boolean {
		const errors: string[] = [];

		// LICENSE_KEY: obrigatoria, nao pode ser vazia
		if (!this.licenseKey || this.licenseKey.trim().length === 0) {
			errors.push('LICENSE_KEY nao esta definida ou esta vazia no .env');
		}

		// LICENSE_SERVER_ADDRESS: obrigatoria, deve ser URL valida
		if (!this.serverAddress || this.serverAddress.trim().length === 0) {
			errors.push(
				'LICENSE_SERVER_ADDRESS nao esta definida ou esta vazia no .env',
			);
		} else if (!this.isValidUrl(this.serverAddress)) {
			errors.push(
				`LICENSE_SERVER_ADDRESS possui URL invalida: "${this.serverAddress}". Formato esperado: http(s)://host:porta`,
			);
		}

		if (errors.length > 0) {
			const reason = errors.join(' | ');

			this.status = {
				isValid: false,
				lastCheckedAt: new Date(),
				reason,
				code: LicenseCodes.LICENSE_MISCONFIGURED,
			};

			this.logger.error(`=== CONFIGURACAO DE LICENCA INVALIDA ===`);
			errors.forEach((err) => this.logger.error(`  → ${err}`));
			this.logger.error(
				`O sistema ficara BLOQUEADO ate que a configuracao seja corrigida no .env e o servidor reiniciado.`,
			);

			return false;
		}

		return true;
	}

	/**
	 * Verifica se uma string e uma URL valida (http ou https).
	 */
	private isValidUrl(value: string): boolean {
		try {
			const url = new URL(value);
			return url.protocol === 'http:' || url.protocol === 'https:';
		} catch {
			return false;
		}
	}

	/**
	 * Heartbeat — revalida a licenca periodicamente.
	 * O intervalo padrao e 5 minutos (configuravel via LICENSE_HEARTBEAT_INTERVAL_MS).
	 */
	@Interval('license-heartbeat', DEFAULT_HEARTBEAT_MS)
	async handleHeartbeat(): Promise<void> {
		if (!this.isConfigured) {
			return;
		}
		this.logger.debug('Heartbeat: revalidando licenca...');
		await this.validateLicense();
	}

	/**
	 * Valida a licenca contra o License Server com retry e backoff.
	 */
	async validateLicense(): Promise<void> {
		try {
			const response = await firstValueFrom(
				this.httpService
					.post<LicenseValidationResponse>(
						`${this.serverAddress}/licenses/validate`,
						{ key: this.licenseKey },
						{
							timeout: 10_000,
							headers: {
								'Content-Type': 'application/json',
								'Content-Encoding': 'utf-8',
								'User-Agent':
									'Amb-Back-License-Validator/1.0.0',
							},
						},
					)
					.pipe(
						retry({
							count: MAX_RETRIES,
							delay: (error, retryCount) => {
								this.logger.warn(
									`Tentativa ${retryCount}/${MAX_RETRIES} falhou: ${error.message}`,
								);
								return timer(RETRY_DELAY_MS * retryCount);
							},
						}),
					),
			);

			const data = response.data;
			this.handleLicenseResponse(data);
		} catch (error: any) {
			this.logger.error(`Falha ao validar licenca: ${error.message}`);
			this.handleNetworkFailure();
		}
	}

	/**
	 * Processa a resposta do License Server e aplica a acao correta
	 * de acordo com o code retornado.
	 */
	private handleLicenseResponse(data: LicenseValidationResponse): void {
		const { code } = data;

		// Licenca valida — tudo OK
		if (data.isValid && code === LicenseCodes.LICENSE_VALIDATED) {
			this.status = {
				isValid: true,
				lastCheckedAt: new Date(),
				reason: undefined,
				license: data.license,
				code,
			};
			this.logger.log(
				`Licenca validada com sucesso: ${data.license?.name ?? 'N/A'}`,
			);
			return;
		}

		// Bloqueio imediato — situacoes irrecuperaveis
		if (IMMEDIATE_BLOCK_CODES.has(code)) {
			this.status = {
				isValid: false,
				lastCheckedAt: new Date(),
				reason: data.reason,
				code,
			};
			this.logger.error(
				`Licenca bloqueada imediatamente [${code}]: ${data.reason ?? 'sem motivo'}`,
			);
			return;
		}

		// Grace period — permite uso temporario
		if (GRACE_PERIOD_CODES.has(code)) {
			this.applyGracePeriod(data.reason, code);
			return;
		}

		// Code desconhecido — trata como bloqueio por seguranca
		this.status = {
			isValid: false,
			lastCheckedAt: new Date(),
			reason: data.reason ?? `Code desconhecido: ${code}`,
			code: code ?? LicenseCodes.LICENSE_INACTIVE,
		};
		this.logger.error(
			`Code de licenca desconhecido [${code}]: bloqueando por seguranca`,
		);
	}

	/**
	 * Quando o License Server esta inacessivel (erro de rede/timeout),
	 * aplica grace period com base no ultimo status valido.
	 */
	private handleNetworkFailure(): void {
		this.applyGracePeriod(
			'License server inacessivel',
			LicenseCodes.LICENSE_SERVER_INACCESSIBLE,
		);
	}

	/**
	 * Aplica a logica de grace period:
	 * - Se o ultimo status era valido e esta dentro do grace period -> mantem valido
	 * - Caso contrario -> invalida
	 */
	private applyGracePeriod(
		reason: string | undefined,
		code: LicenseCodes,
	): void {
		// Se nunca foi valido, bloqueia direto
		if (!this.status.isValid) {
			this.status = {
				isValid: false,
				lastCheckedAt: this.status.lastCheckedAt,
				reason: reason ?? 'Licenca invalida',
				code,
			};
			this.logger.warn(
				`Licenca invalida [${code}]: ${reason ?? 'sem motivo'}`,
			);
			return;
		}

		// Calcula quanto tempo passou desde a ultima validacao bem-sucedida
		const elapsed = Date.now() - this.status.lastCheckedAt.getTime();

		if (elapsed < this.gracePeriodMs) {
			const remainingHours = Math.round(
				(this.gracePeriodMs - elapsed) / (60 * 60 * 1000),
			);
			this.logger.warn(
				`Grace period ativo [${code}] — licenca valida por mais ~${remainingHours}h`,
			);
			// Mantem isValid = true, nao atualiza lastCheckedAt
		} else {
			this.logger.error(
				`Grace period expirado [${code}] — licenca marcada como invalida`,
			);
			this.status = {
				isValid: false,
				lastCheckedAt: this.status.lastCheckedAt,
				reason: `${reason ?? 'Problema de licenca'} e grace period expirado`,
				code,
			};
		}
	}

	/**
	 * Retorna se a licenca esta valida (usado pelo LicenseGuard).
	 */
	getValidationStatus(): boolean {
		return this.status.isValid;
	}

	/**
	 * Retorna o status completo da licenca (para diagnostico/health check).
	 */
	getLicenseStatus(): LicenseStatus {
		return { ...this.status };
	}
}
