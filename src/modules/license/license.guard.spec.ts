import { ExecutionContext, ForbiddenException, Logger } from '@nestjs/common';
import { LicenseGuard } from './license.guard';
import { LicenseService } from './license.service';
import { LicenseCodes, LicenseStatus } from './license.interfaces';

describe('LicenseGuard', () => {
	let guard: LicenseGuard;
	let licenseService: Partial<LicenseService>;

	const mockExecutionContext = {} as ExecutionContext;

	beforeEach(() => {
		jest.spyOn(Logger.prototype, 'log').mockImplementation();
		jest.spyOn(Logger.prototype, 'error').mockImplementation();
		jest.spyOn(Logger.prototype, 'warn').mockImplementation();
		jest.spyOn(Logger.prototype, 'debug').mockImplementation();
		jest.spyOn(Logger.prototype, 'verbose').mockImplementation();
		licenseService = {
			getValidationStatus: jest.fn(),
			getLicenseStatus: jest.fn(),
		};

		guard = new LicenseGuard(licenseService as LicenseService);
	});

	it('should be defined', () => {
		expect(guard).toBeDefined();
	});

	it('deve permitir acesso quando a licenca e valida', () => {
		jest.spyOn(licenseService, 'getValidationStatus').mockReturnValue(true);

		expect(guard.canActivate(mockExecutionContext)).toBe(true);
	});

	it('deve bloquear acesso quando a licenca e invalida', () => {
		jest.spyOn(licenseService, 'getValidationStatus').mockReturnValue(
			false,
		);

		const mockStatus: LicenseStatus = {
			isValid: false,
			lastCheckedAt: new Date(),
			reason: 'Licenca expirada',
			code: LicenseCodes.LICENSE_EXPIRED,
		};
		jest.spyOn(licenseService, 'getLicenseStatus').mockReturnValue(
			mockStatus,
		);

		expect(() => guard.canActivate(mockExecutionContext)).toThrow(
			ForbiddenException,
		);
	});

	it('deve incluir o code e motivo na resposta de erro', () => {
		jest.spyOn(licenseService, 'getValidationStatus').mockReturnValue(
			false,
		);

		const mockStatus: LicenseStatus = {
			isValid: false,
			lastCheckedAt: new Date(),
			reason: 'Organizacao esta inativa',
			code: LicenseCodes.LICENSE_ORGANIZATION_INACTIVE,
		};
		jest.spyOn(licenseService, 'getLicenseStatus').mockReturnValue(
			mockStatus,
		);

		try {
			guard.canActivate(mockExecutionContext);
			fail('Deveria ter lancado ForbiddenException');
		} catch (e) {
			const response = (e as ForbiddenException).getResponse() as any;
			expect(response.code).toBe(
				LicenseCodes.LICENSE_ORGANIZATION_INACTIVE,
			);
			expect(response.reason).toBe('Organizacao esta inativa');
		}
	});
});
