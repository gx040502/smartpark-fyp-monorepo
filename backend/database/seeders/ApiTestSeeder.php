<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Carbon;
use App\Models\ParkingSession;
use App\Models\PaymentReceipt;
use App\Models\ExitAlert;
use App\Enums\ParkingStatus;
use Illuminate\Support\Str;

class ApiTestSeeder extends Seeder
{
    public function run()
    {
        // ----------------------------------------------------------------------
        // RESET PATH
        // Delete existing test sessions (any plate starting with TEST)
        // Cascade will normally handle receipts/alerts, but we do it manually to be safe
        // ----------------------------------------------------------------------
        $this->command->info('Resetting API test data...');
        
        $testSessions = ParkingSession::where('license_plate', 'like', 'TEST%')->get();
        $testSessionIds = $testSessions->pluck('id')->toArray();
        
        if (!empty($testSessionIds)) {
            PaymentReceipt::whereIn('parking_session_id', $testSessionIds)->delete();
            ExitAlert::whereIn('session_id', $testSessionIds)->delete();
            // Also delete any orphaned exit alerts for these plates
            ExitAlert::where('license_plate', 'like', 'TEST%')->delete();
            ParkingSession::whereIn('id', $testSessionIds)->delete();
        }

        // Delete the ZZZ9999 orphan alert if it exists
        ExitAlert::where('license_plate', 'ZZZ9999')->delete();

        // Delete test user to ensure API-01 Register always passes
        \App\Models\User::where('email', 'test@test.com')->delete();

        // ----------------------------------------------------------------------
        // SEED PATH
        // ----------------------------------------------------------------------
        $this->command->info('Seeding API test data...');

        $now = Carbon::now();

        // Helper to create receipt
        $createReceipt = function ($sessionId, $amount, $date) {
            PaymentReceipt::create([
                'parking_session_id' => $sessionId,
                'receipt_number'     => 'RCP-' . strtoupper(Str::random(8)),
                'total_amount'       => $amount,
                'payment_date'       => $date,
                'payment_method'     => 'Credit Card',
                'payment_type'       => 'initial',
            ]);
        };

        // 1. TEST0016: Free exit (status ENTER, entry_time 12 mins ago)
        ParkingSession::create([
            'license_plate' => 'TEST0016',
            'color'         => 'White',
            'model'         => 'Sedan',
            'status'        => ParkingStatus::ENTER->value,
            'entry_time'    => $now->copy()->subMinutes(12),
            'amount_due'    => 0,
        ]);

        // 2. TEST0017: Normal paid exit (status PAID, entry_time 2 hours ago, grace_end_time in the future)
        $session17 = ParkingSession::create([
            'license_plate'  => 'TEST0017',
            'color'          => 'White',
            'model'          => 'Sedan',
            'status'         => ParkingStatus::PAID->value,
            'entry_time'     => $now->copy()->subHours(2),
            'grace_end_time' => $now->copy()->addMinutes(10), // Future
            'amount_due'     => 4.00,
        ]);
        $createReceipt($session17->id, 4.00, $now->copy()->subMinutes(5));

        // 3. TEST0018: Unpaid (status ENTER, entry_time 2 hours ago)
        ParkingSession::create([
            'license_plate' => 'TEST0018',
            'color'         => 'White',
            'model'         => 'Sedan',
            'status'        => ParkingStatus::ENTER->value,
            'entry_time'    => $now->copy()->subHours(2),
            'amount_due'    => 4.00,
        ]);

        // 4. TEST0019: Grace expired (status PAID, entry_time 3 hours ago, grace_end_time in the past)
        $session19 = ParkingSession::create([
            'license_plate'  => 'TEST0019',
            'color'          => 'White',
            'model'          => 'Sedan',
            'status'         => ParkingStatus::PAID->value,
            'entry_time'     => $now->copy()->subHours(3),
            'grace_end_time' => $now->copy()->subMinutes(5), // Past
            'amount_due'     => 6.00,
        ]);
        $createReceipt($session19->id, 6.00, $now->copy()->subMinutes(20));

        // 5. TEST0020: Attribute mismatch (status PAID, entry_time 2 hours ago, grace_end_time future, colour Blue)
        $session20 = ParkingSession::create([
            'license_plate'  => 'TEST0020',
            'color'          => 'Blue', // We will send 'Green' in the API request
            'model'          => 'Sedan',
            'status'         => ParkingStatus::PAID->value,
            'entry_time'     => $now->copy()->subHours(2),
            'grace_end_time' => $now->copy()->addMinutes(10), // Future
            'amount_due'     => 4.00,
        ]);
        $createReceipt($session20->id, 4.00, $now->copy()->subMinutes(5));

        // 6. TEST0021: API-15 Pay-additional (PAID, grace expired)
        $session21 = ParkingSession::create([
            'license_plate'  => 'TEST0021',
            'color'          => 'White',
            'model'          => 'SUV',
            'status'         => ParkingStatus::PAID->value,
            'entry_time'     => $now->copy()->subHours(4),
            'grace_end_time' => $now->copy()->subMinutes(30), // Past
            'amount_due'     => 8.00,
        ]);
        $createReceipt($session21->id, 8.00, $now->copy()->subMinutes(45));

        // 7. TEST0022: API-16 Pay-additional rejected (PAID, grace NOT expired)
        $session22 = ParkingSession::create([
            'license_plate'  => 'TEST0022',
            'color'          => 'White',
            'model'          => 'SUV',
            'status'         => ParkingStatus::PAID->value,
            'entry_time'     => $now->copy()->subHours(1),
            'grace_end_time' => $now->copy()->addMinutes(12), // Future
            'amount_due'     => 2.00,
        ]);
        $createReceipt($session22->id, 2.00, $now->copy()->subMinutes(3));

        $this->command->info('API test data seeded successfully.');
    }
}
