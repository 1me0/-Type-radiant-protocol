export interface ProofStatus {
    user: string;
    status: 'Pending' | 'Valid' | 'Slashed';
    hash?: string;
    reward?: string;
}
