import {
	CanActivate,
	ExecutionContext,
	ForbiddenException,
	Injectable,
	Logger,
} from '@nestjs/common';
import { LicenseService } from './license.service';

@Injectable()
export class LicenseGuard implements CanActivate {
	private readonly logger = new Logger(LicenseGuard.name);

	constructor(private readonly licenseService: LicenseService) {}

	canActivate(context: ExecutionContext): boolean {
		const isValid = this.licenseService.getValidationStatus();

		if (!isValid) {
			const status = this.licenseService.getLicenseStatus();
			const reason = status.reason ?? 'Motivo desconhecido';
			const code = status.code;

			this.logger.warn(`Acesso bloqueado [${code}]: ${reason}`);

			throw new ForbiddenException({
				message: `Licenca invalida ou expirada: ${reason}`,
				code,
				reason,
			});
		}

		return true;
	}
}
