/**
 * Contrato da resposta da API de validação do License Server.
 * Corresponde ao retorno de POST /licenses/validate no Backend-Core.
 */
export interface LicenseValidationResponse {
	isValid: boolean;
	license?: {
		id: string;
		name: string;
		expiresAt: string | null;
		organization: { id: string; name: string };
		licenseType: {
			id: string;
			name: string;
			maxSeats: number | null;
		};
		seatsUsed: number;
		seatsAvailable: number | null;
	};
	reason?: string;
	code: LicenseCodes;
}

/**
 * Estado interno da licença no client server,
 * incluindo metadados de cache e grace period.
 */
export interface LicenseStatus {
	isValid: boolean;
	lastCheckedAt: Date;
	reason?: string;
	license?: LicenseValidationResponse['license'];
	code: LicenseCodes;
}

export enum LicenseCodes {
	LICENSE_TO_VALIDATE = 'LICENSE_TO_VALIDATE',
	LICENSE_MISCONFIGURED = 'LICENSE_MISCONFIGURED',
	LICENSE_NOT_FOUND = 'LICENSE_NOT_FOUND',
	LICENSE_DELETED = 'LICENSE_DELETED',
	LICENSE_INACTIVE = 'LICENSE_INACTIVE',
	LICENSE_ORGANIZATION_INACTIVE = 'LICENSE_ORGANIZATION_INACTIVE',
	LICENSE_EXPIRED = 'LICENSE_EXPIRED',
	LICENSE_SEATS_EXCEEDED = 'LICENSE_SEATS_EXCEEDED',
	LICENSE_SERVER_INACCESSIBLE = 'LICENSE_SERVER_INACCESSIBLE',
	LICENSE_VALIDATED = 'LICENSE_VALIDATED',
}
