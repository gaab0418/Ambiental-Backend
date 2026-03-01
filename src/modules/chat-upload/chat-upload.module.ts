import { Module } from '@nestjs/common';
import { ChatUploadService } from './chat-upload.service';
import { ChatUploadController } from './chat-upload.controller';
import { ChatModule } from '../chat/chat.module';
import { LicenseModule } from '../license/license.module';

@Module({
	imports: [ChatModule, LicenseModule],
	controllers: [ChatUploadController],
	providers: [ChatUploadService],
	exports: [ChatUploadService],
})
export class ChatUploadModule {}
