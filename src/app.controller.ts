import { Controller, Get, HttpStatus } from '@nestjs/common';
import { AppService } from './app.service';
import { ApiResponse, ApiTags } from '@nestjs/swagger';

@Controller('app')
@ApiTags('System')
export class AppController {
	constructor(private readonly appService: AppService) {}

	@Get('health')
	@ApiResponse({
		status: HttpStatus.OK,
		description: 'Health check',
		schema: {
			type: 'object',
			properties: {
				status: {
					type: 'string',
				},
				timestamp: {
					type: 'string',
				},
			},
		},
	})
	healthCheck(): Object {
		return this.appService.healthCheck();
	}

	@Get('license')
	@ApiResponse({
		status: HttpStatus.OK,
		description: 'License check',
		schema: {
			type: 'object',
			properties: {
				isValid: {
					type: 'boolean',
				},
				reason: {
					type: 'string',
				},
			},
		},
	})
	licenseCheck(): Object {
		return this.appService.isLicenseOk();
	}
}
