import { Module } from '@nestjs/common';
import { MessageService } from './message.service';
import { MessageController } from './message.controller';
import { ChatModule } from '../chat/chat.module';
import { LicenseModule } from '../license/license.module';

@Module({
	imports: [ChatModule, LicenseModule],
	controllers: [MessageController],
	providers: [MessageService],
	exports: [MessageService],
})
export class MessageModule {}
