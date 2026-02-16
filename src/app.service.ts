import { Injectable } from '@nestjs/common';
import { LicenseService } from './modules/license/license.service';

@Injectable()
export class AppService {
	constructor(private readonly licenseService: LicenseService) {}

	healthCheck(): Object {
		return {
			status: 'ok',
			timestamp: new Date().toISOString(),
		};
	}

	isLicenseOk() {
		const { lastCheckedAt, code, ...returnData } =
			this.licenseService.getLicenseStatus();
		return returnData;
	}
}
