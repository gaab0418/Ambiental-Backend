import { Module } from '@nestjs/common';
import { ProcessService } from './process.service';
import { ProcessController } from './process.controller';
import { LicenseModule } from '../license/license.module';

@Module({
	imports: [LicenseModule],
	controllers: [ProcessController],
	providers: [ProcessService],
	exports: [ProcessService],
})
export class ProcessModule {}
