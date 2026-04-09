<?php

namespace Database\Seeders;

use App\Enums\ParkingStatus;
use App\Models\ParkingSession;
use App\Models\PaymentReceipt;
use App\Models\User;
use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    /**
     * Seed the application's database.
     */
    public function run(): void
    {
        // ─── 1. Admin User ───────────────────────────────────────────
        User::factory()->create([
            'name'     => 'Admin',
            'email'    => 'admin@smartpark.com',
            'password' => bcrypt('password'),
        ]);

        $this->command->info('✓ Admin user created: admin@smartpark.com / password');

        // ─── 2. Parking Sessions (50 records) ────────────────────────
        $sessions = ParkingSession::factory()->count(50)->create();

        $this->command->info('✓ Created 50 parking sessions');

        // ─── 3. Payment Receipts for PAID and COMPLETED sessions ─────
        $receiptCount = 0;

        $sessions->each(function (ParkingSession $session) use (&$receiptCount) {
            if (in_array($session->status, [ParkingStatus::PAID, ParkingStatus::COMPLETED])) {
                PaymentReceipt::factory()
                    ->forSession($session)
                    ->create();

                $receiptCount++;
            }
        });

        $this->command->info("✓ Created {$receiptCount} payment receipts");

        // ─── Summary ─────────────────────────────────────────────────
        $this->command->newLine();
        $this->command->info('=== Seeding Summary ===');
        $this->command->info('Users:            ' . User::count());
        $this->command->info('Parking Sessions: ' . ParkingSession::count());
        $this->command->info('  - ENTER:        ' . ParkingSession::where('status', ParkingStatus::ENTER)->count());
        $this->command->info('  - PAID:         ' . ParkingSession::where('status', ParkingStatus::PAID)->count());
        $this->command->info('  - COMPLETED:    ' . ParkingSession::where('status', ParkingStatus::COMPLETED)->count());
        $this->command->info('Payment Receipts: ' . PaymentReceipt::count());
    }
}
