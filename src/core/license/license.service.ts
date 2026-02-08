import { Injectable, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class LicenseService implements OnModuleInit {
	private isLicenseValid = false;

	constructor(private readonly configService: ConfigService) {}

	async onModuleInit() {
		await this.refreshLicense();
	}

	async refreshLicense() {
		const licenseServerAddress = this.configService.get<string>(
			'LICENSE_SERVER_ADDRESS',
		);
		try {
			// Aqui você envia o ID da máquina e a chave do cliente
			const response = await fetch(licenseServerAddress + '/license', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					key: this.configService.get<string>('LICENSE_KEY'),
				}),
			});
			const data = await response.json();
			this.isLicenseValid = data.active;
		} catch (e) {
			// Se falhar, você decide: bloqueia ou dá 24h de carência?
			this.isLicenseValid = false;
		}
	}

	getValidationStatus() {
		return this.isLicenseValid;
	}
}
