import {
	CanActivate,
	ExecutionContext,
	ForbiddenException,
	Injectable,
} from '@nestjs/common';
import { LicenseService } from './license.service';

@Injectable()
export class LicenseGuard implements CanActivate {
	constructor(private licenseService: LicenseService) {}

	canActivate(context: ExecutionContext): boolean {
		const isValid = this.licenseService.getValidationStatus();
		if (!isValid) {
			throw new ForbiddenException('Licença inválida ou expirada.');
		}
		return true;
	}
}
