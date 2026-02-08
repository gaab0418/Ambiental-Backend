import { LicenseGuard } from './license.guard';

describe('LicenseGuard', () => {
  it('should be defined', () => {
    expect(new LicenseGuard()).toBeDefined();
  });
});
