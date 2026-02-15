import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { LicenseService } from './license.service';
import { LicenseGuard } from './license.guard';

@Module({
	imports: [
		HttpModule.register({
			timeout: 10_000,
			maxRedirects: 3,
		}),
	],
	providers: [LicenseService, LicenseGuard],
	exports: [LicenseService, LicenseGuard],
})
export class LicenseModule {}
