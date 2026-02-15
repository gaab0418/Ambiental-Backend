import { Logger } from '@nestjs/common';
import { Test, TestingModule } from '@nestjs/testing';
import { ConfigService } from '@nestjs/config';
import { HttpService } from '@nestjs/axios';
import { of, throwError } from 'rxjs';
import { AxiosResponse, AxiosHeaders } from 'axios';
import { LicenseService } from './license.service';
import { LicenseCodes, LicenseValidationResponse } from './license.interfaces';

const mockAxiosHeaders = new AxiosHeaders();

function createAxiosResponse<T>(data: T): AxiosResponse<T> {
	return {
		data,
		status: 200,
		statusText: 'OK',
		headers: {},
		config: { headers: mockAxiosHeaders },
	};
}

function validLicenseResponse(): LicenseValidationResponse {
	return {
		isValid: true,
		code: LicenseCodes.LICENSE_VALIDATED,
		license: {
			id: '1',
			name: 'Licenca Teste',
			expiresAt: null,
			organization: { id: '1', name: 'Org Teste' },
			licenseType: { id: '1', name: 'Premium', maxSeats: 10 },
			seatsUsed: 2,
			seatsAvailable: 8,
		},
	};
}

describe('LicenseService', () => {
	let service: LicenseService;
	let httpService: HttpService;

	const mockConfigValues: Record<string, string> = {
		LICENSE_SERVER_ADDRESS: 'http://localhost:3005',
		LICENSE_KEY: 'TEST-KEY-1234',
		LICENSE_GRACE_PERIOD_HOURS: '24',
	};

	beforeEach(async () => {
		jest.useFakeTimers();
		jest.spyOn(Logger.prototype, 'log').mockImplementation();
		jest.spyOn(Logger.prototype, 'error').mockImplementation();
		jest.spyOn(Logger.prototype, 'warn').mockImplementation();
		jest.spyOn(Logger.prototype, 'debug').mockImplementation();
		jest.spyOn(Logger.prototype, 'verbose').mockImplementation();

		const module: TestingModule = await Test.createTestingModule({
			providers: [
				LicenseService,
				{
					provide: ConfigService,
					useValue: {
						get: jest.fn((key: string, defaultValue?: any) => {
							return mockConfigValues[key] ?? defaultValue;
						}),
					},
				},
				{
					provide: HttpService,
					useValue: {
						post: jest.fn(),
					},
				},
			],
		}).compile();

		service = module.get<LicenseService>(LicenseService);
		httpService = module.get<HttpService>(HttpService);
	});

	afterEach(() => {
		jest.useRealTimers();
	});

	it('should be defined', () => {
		expect(service).toBeDefined();
	});

	describe('LICENSE_VALIDATED', () => {
		it('deve marcar licenca como valida', async () => {
			const response = validLicenseResponse();
			jest.spyOn(httpService, 'post').mockReturnValue(
				of(createAxiosResponse(response)),
			);

			await service.validateLicense();

			expect(service.getValidationStatus()).toBe(true);
			const status = service.getLicenseStatus();
			expect(status.code).toBe(LicenseCodes.LICENSE_VALIDATED);
			expect(status.license?.name).toBe('Licenca Teste');
		});
	});

	describe('Bloqueio imediato (IMMEDIATE_BLOCK_CODES)', () => {
		const immediateBlockCodes = [
			{
				code: LicenseCodes.LICENSE_NOT_FOUND,
				reason: 'Licenca nao encontrada',
			},
			{
				code: LicenseCodes.LICENSE_DELETED,
				reason: 'Licenca foi removida',
			},
			{
				code: LicenseCodes.LICENSE_INACTIVE,
				reason: 'Licenca esta inativa',
			},
			{
				code: LicenseCodes.LICENSE_ORGANIZATION_INACTIVE,
				reason: 'Organizacao esta inativa',
			},
		];

		it.each(immediateBlockCodes)(
			'deve bloquear imediatamente com code $code',
			async ({ code, reason }) => {
				const response: LicenseValidationResponse = {
					isValid: false,
					code,
					reason,
				};
				jest.spyOn(httpService, 'post').mockReturnValue(
					of(createAxiosResponse(response)),
				);

				await service.validateLicense();

				expect(service.getValidationStatus()).toBe(false);
				expect(service.getLicenseStatus().code).toBe(code);
				expect(service.getLicenseStatus().reason).toBe(reason);
			},
		);

		it('deve bloquear imediatamente mesmo com grace period anterior', async () => {
			// Primeiro: validacao com sucesso
			jest.spyOn(httpService, 'post').mockReturnValueOnce(
				of(createAxiosResponse(validLicenseResponse())),
			);
			await service.validateLicense();
			expect(service.getValidationStatus()).toBe(true);

			// Segundo: organizacao inativa — bloqueio imediato, sem grace period
			const response: LicenseValidationResponse = {
				isValid: false,
				code: LicenseCodes.LICENSE_ORGANIZATION_INACTIVE,
				reason: 'Organizacao esta inativa',
			};
			jest.spyOn(httpService, 'post').mockReturnValue(
				of(createAxiosResponse(response)),
			);

			await service.validateLicense();

			expect(service.getValidationStatus()).toBe(false);
			expect(service.getLicenseStatus().code).toBe(
				LicenseCodes.LICENSE_ORGANIZATION_INACTIVE,
			);
		});
	});

	describe('Grace period (GRACE_PERIOD_CODES)', () => {
		it('deve manter licenca valida durante grace period para LICENSE_EXPIRED', async () => {
			// Validacao com sucesso
			jest.spyOn(httpService, 'post').mockReturnValueOnce(
				of(createAxiosResponse(validLicenseResponse())),
			);
			await service.validateLicense();
			expect(service.getValidationStatus()).toBe(true);

			// Licenca expirada — grace period
			const response: LicenseValidationResponse = {
				isValid: false,
				code: LicenseCodes.LICENSE_EXPIRED,
				reason: 'Licenca expirada',
			};
			jest.spyOn(httpService, 'post').mockReturnValue(
				of(createAxiosResponse(response)),
			);

			await service.validateLicense();

			// Ainda valida por causa do grace period
			expect(service.getValidationStatus()).toBe(true);
		});

		it('deve manter licenca valida durante grace period quando server esta inacessivel', async () => {
			// Validacao com sucesso
			jest.spyOn(httpService, 'post').mockReturnValueOnce(
				of(createAxiosResponse(validLicenseResponse())),
			);
			await service.validateLicense();
			expect(service.getValidationStatus()).toBe(true);

			// Erro de rede
			jest.spyOn(httpService, 'post').mockReturnValue(
				throwError(() => new Error('ECONNREFUSED')),
			);

			const validatePromise = service.validateLicense();
			jest.advanceTimersByTime(30_000);
			await validatePromise;

			expect(service.getValidationStatus()).toBe(true);
		});

		it('deve bloquear quando nao havia validacao valida anterior', async () => {
			jest.spyOn(httpService, 'post').mockReturnValue(
				throwError(() => new Error('ECONNREFUSED')),
			);

			const validatePromise = service.validateLicense();
			jest.advanceTimersByTime(30_000);
			await validatePromise;

			expect(service.getValidationStatus()).toBe(false);
			expect(service.getLicenseStatus().code).toBe(
				LicenseCodes.LICENSE_SERVER_INACCESSIBLE,
			);
		});
	});

	describe('getLicenseStatus', () => {
		it('deve retornar uma copia defensiva do status', () => {
			const status1 = service.getLicenseStatus();
			const status2 = service.getLicenseStatus();

			expect(status1).toEqual(status2);
			expect(status1).not.toBe(status2);
		});
	});

	describe('Validacao de configuracao (LICENSE_MISCONFIGURED)', () => {
		async function createServiceWithConfig(
			config: Record<string, string>,
		): Promise<{ service: LicenseService; httpService: HttpService }> {
			const module: TestingModule = await Test.createTestingModule({
				providers: [
					LicenseService,
					{
						provide: ConfigService,
						useValue: {
							get: jest.fn((key: string, defaultValue?: any) => {
								return config[key] ?? defaultValue;
							}),
						},
					},
					{
						provide: HttpService,
						useValue: { post: jest.fn() },
					},
				],
			}).compile();

			return {
				service: module.get(LicenseService),
				httpService: module.get(HttpService),
			};
		}

		it('deve bloquear com LICENSE_MISCONFIGURED quando LICENSE_KEY esta vazia', async () => {
			const { service: svc } = await createServiceWithConfig({
				LICENSE_SERVER_ADDRESS: 'http://localhost:3005',
				LICENSE_KEY: '',
			});

			await svc.onModuleInit();

			expect(svc.getValidationStatus()).toBe(false);
			expect(svc.getLicenseStatus().code).toBe(
				LicenseCodes.LICENSE_MISCONFIGURED,
			);
			expect(svc.getLicenseStatus().reason).toContain('LICENSE_KEY');
		});

		it('deve bloquear com LICENSE_MISCONFIGURED quando LICENSE_SERVER_ADDRESS esta vazia', async () => {
			const { service: svc } = await createServiceWithConfig({
				LICENSE_SERVER_ADDRESS: '',
				LICENSE_KEY: 'VALID-KEY',
			});

			await svc.onModuleInit();

			expect(svc.getValidationStatus()).toBe(false);
			expect(svc.getLicenseStatus().code).toBe(
				LicenseCodes.LICENSE_MISCONFIGURED,
			);
			expect(svc.getLicenseStatus().reason).toContain(
				'LICENSE_SERVER_ADDRESS',
			);
		});

		it('deve bloquear com LICENSE_MISCONFIGURED quando LICENSE_SERVER_ADDRESS nao e URL valida', async () => {
			const { service: svc } = await createServiceWithConfig({
				LICENSE_SERVER_ADDRESS: 'nao-e-uma-url',
				LICENSE_KEY: 'VALID-KEY',
			});

			await svc.onModuleInit();

			expect(svc.getValidationStatus()).toBe(false);
			expect(svc.getLicenseStatus().code).toBe(
				LicenseCodes.LICENSE_MISCONFIGURED,
			);
			expect(svc.getLicenseStatus().reason).toContain('URL invalida');
		});

		it('deve reportar multiplos erros quando ambas as variaveis estao invalidas', async () => {
			const { service: svc } = await createServiceWithConfig({
				LICENSE_SERVER_ADDRESS: '',
				LICENSE_KEY: '',
			});

			await svc.onModuleInit();

			expect(svc.getValidationStatus()).toBe(false);
			const status = svc.getLicenseStatus();
			expect(status.code).toBe(LicenseCodes.LICENSE_MISCONFIGURED);
			expect(status.reason).toContain('LICENSE_KEY');
			expect(status.reason).toContain('LICENSE_SERVER_ADDRESS');
		});

		it('nao deve chamar o license server quando configuracao esta invalida', async () => {
			const { service: svc, httpService: http } =
				await createServiceWithConfig({
					LICENSE_SERVER_ADDRESS: 'http://localhost:3005',
					LICENSE_KEY: '',
				});

			await svc.onModuleInit();

			expect(http.post).not.toHaveBeenCalled();
		});

		it('heartbeat nao deve rodar quando configuracao esta invalida', async () => {
			const { service: svc, httpService: http } =
				await createServiceWithConfig({
					LICENSE_SERVER_ADDRESS: 'http://localhost:3005',
					LICENSE_KEY: '',
				});

			await svc.onModuleInit();
			await svc.handleHeartbeat();

			expect(http.post).not.toHaveBeenCalled();
		});
	});
});
