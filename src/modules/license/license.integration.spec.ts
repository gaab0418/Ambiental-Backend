import { Test, TestingModule } from '@nestjs/testing';
import { ConfigService } from '@nestjs/config';
import { HttpService } from '@nestjs/axios';
import { Logger } from '@nestjs/common';
import { ForbiddenException } from '@nestjs/common';
import { of, throwError } from 'rxjs';
import { AxiosResponse, AxiosHeaders } from 'axios';
import { LicenseService } from './license.service';
import { LicenseGuard } from './license.guard';
import { LicenseCodes, LicenseValidationResponse } from './license.interfaces';

/**
 * Testes de integracao: Service + Guard juntos.
 * Valida o fluxo real: License Server retorna um code → Service processa
 * → Guard bloqueia ou permite a request.
 */

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

describe('License Integration (Service + Guard)', () => {
	let service: LicenseService;
	let guard: LicenseGuard;
	let httpService: HttpService;

	const mockContext = {} as any; // ExecutionContext simplificado

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
				LicenseGuard,
				{
					provide: ConfigService,
					useValue: {
						get: jest.fn((key: string, defaultValue?: any) => {
							const values: Record<string, string> = {
								LICENSE_SERVER_ADDRESS: 'http://localhost:3005',
								LICENSE_KEY: 'TEST-KEY-1234',
								LICENSE_GRACE_PERIOD_HOURS: '24',
							};
							return values[key] ?? defaultValue;
						}),
					},
				},
				{
					provide: HttpService,
					useValue: { post: jest.fn() },
				},
			],
		}).compile();

		service = module.get(LicenseService);
		guard = module.get(LicenseGuard);
		httpService = module.get(HttpService);
	});

	afterEach(() => {
		jest.useRealTimers();
	});

	// ==================== ACESSO LIBERADO ====================

	it('LICENSE_VALIDATED → guard permite acesso', async () => {
		jest.spyOn(httpService, 'post').mockReturnValue(
			of(createAxiosResponse(validLicenseResponse())),
		);

		await service.validateLicense();

		expect(guard.canActivate(mockContext)).toBe(true);
	});

	// ==================== BLOQUEIO IMEDIATO ====================

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
		'$code → guard bloqueia com ForbiddenException',
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

			// Guard DEVE lancar ForbiddenException
			expect(() => guard.canActivate(mockContext)).toThrow(
				ForbiddenException,
			);

			// E a exception deve conter o code correto
			try {
				guard.canActivate(mockContext);
			} catch (e) {
				const body = (e as ForbiddenException).getResponse() as any;
				expect(body.code).toBe(code);
				expect(body.reason).toBe(reason);
			}
		},
	);

	it('Bloqueio imediato ignora grace period — mesmo apos validacao bem-sucedida', async () => {
		// 1. Licenca valida
		jest.spyOn(httpService, 'post').mockReturnValueOnce(
			of(createAxiosResponse(validLicenseResponse())),
		);
		await service.validateLicense();
		expect(guard.canActivate(mockContext)).toBe(true);

		// 2. Organizacao deletada → deve bloquear IMEDIATAMENTE
		jest.spyOn(httpService, 'post').mockReturnValue(
			of(
				createAxiosResponse<LicenseValidationResponse>({
					isValid: false,
					code: LicenseCodes.LICENSE_DELETED,
					reason: 'Licenca foi removida',
				}),
			),
		);
		await service.validateLicense();

		expect(() => guard.canActivate(mockContext)).toThrow(
			ForbiddenException,
		);
	});

	// ==================== GRACE PERIOD ====================

	it('LICENSE_EXPIRED → guard permite acesso durante grace period', async () => {
		// 1. Licenca valida
		jest.spyOn(httpService, 'post').mockReturnValueOnce(
			of(createAxiosResponse(validLicenseResponse())),
		);
		await service.validateLicense();
		expect(guard.canActivate(mockContext)).toBe(true);

		// 2. Licenca expirada — grace period ativo
		jest.spyOn(httpService, 'post').mockReturnValue(
			of(
				createAxiosResponse<LicenseValidationResponse>({
					isValid: false,
					code: LicenseCodes.LICENSE_EXPIRED,
					reason: 'Licenca expirada',
				}),
			),
		);
		await service.validateLicense();

		// Guard DEVE permitir (grace period)
		expect(guard.canActivate(mockContext)).toBe(true);
	});

	it('Server inacessivel → guard permite acesso durante grace period', async () => {
		// 1. Licenca valida
		jest.spyOn(httpService, 'post').mockReturnValueOnce(
			of(createAxiosResponse(validLicenseResponse())),
		);
		await service.validateLicense();
		expect(guard.canActivate(mockContext)).toBe(true);

		// 2. Server cai
		jest.spyOn(httpService, 'post').mockReturnValue(
			throwError(() => new Error('ECONNREFUSED')),
		);

		const p = service.validateLicense();
		jest.advanceTimersByTime(30_000);
		await p;

		// Guard DEVE permitir (grace period)
		expect(guard.canActivate(mockContext)).toBe(true);
	});

	it('Server inacessivel sem validacao anterior → guard bloqueia', async () => {
		jest.spyOn(httpService, 'post').mockReturnValue(
			throwError(() => new Error('ECONNREFUSED')),
		);

		const p = service.validateLicense();
		jest.advanceTimersByTime(30_000);
		await p;

		expect(() => guard.canActivate(mockContext)).toThrow(
			ForbiddenException,
		);
	});
});
