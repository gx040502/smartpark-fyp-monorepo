<?php

namespace App\Console\Commands;

use App\Enums\ParkingStatus;
use App\Models\ParkingSession;
use App\Models\PaymentReceipt;
use App\Models\ExitAlert;
use Illuminate\Console\Command;
use Illuminate\Support\Carbon;
use Illuminate\Support\Str;

class SetupDemoData extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'app:setup-demo';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Structures the existing LPR parking sessions into a perfect demo state for presentations.';

    /**
     * Execute the console command.
     */
    public function handle()
    {
        $this->info('Starting Demo Data Setup...');

        // 1. Clear old receipts and alerts to prevent duplicates
        PaymentReceipt::truncate();
        ExitAlert::truncate();
        $this->info('✓ Cleared old payment receipts and exit alerts.');

        // Get all sessions
        $sessions = ParkingSession::all();

        if ($sessions->count() < 13) {
            $this->warn("Warning: You only have {$sessions->count()} records in the database. The demo might not look complete.");
        }

        // Convert collection to array for easier popping/manipulation
        $sessionArray = $sessions->all();
        shuffle($sessionArray); // Shuffle so it's not always the same cars doing the same things

        // Find the Tesla first
        $teslaKey = -1;
        foreach ($sessionArray as $key => $session) {
            if (strtolower($session->model) === 'tesla') {
                $teslaKey = $key;
                break;
            }
        }

        if ($teslaKey !== -1) {
            $tesla = $sessionArray[$teslaKey];
            unset($sessionArray[$teslaKey]);
            $this->setupTesla($tesla);
        } else {
            $this->warn('Warning: No Tesla found in the database. Model mismatch scenario will be skipped.');
        }

        // Re-index array after unsetting
        $sessionArray = array_values($sessionArray);

        // 2. Setup Grace Period Scenario (1 Car)
        if (count($sessionArray) > 0) {
            $graceCar = array_pop($sessionArray);
            $this->setupGracePeriodCar($graceCar);
        }

        // 3. Setup Today's Live Cars (2 Cars)
        if (count($sessionArray) > 0) {
            $freeCar = array_pop($sessionArray);
            $this->setupFreeExitCar($freeCar);
        }
        if (count($sessionArray) > 0) {
            $normalLiveCar = array_pop($sessionArray);
            $this->setupNormalLiveCar($normalLiveCar);
        }

        // 4. Setup This Week's Revenue (5 Cars)
        $weekCarsCount = min(5, count($sessionArray));
        for ($i = 0; $i < $weekCarsCount; $i++) {
            $weekCar = array_pop($sessionArray);
            $this->setupWeekCar($weekCar);
        }

        // 5. Setup Past Months' Revenue (Remaining Cars)
        $monthCarsCount = count($sessionArray);
        for ($i = 0; $i < $monthCarsCount; $i++) {
            $monthCar = array_pop($sessionArray);
            $this->setupMonthCar($monthCar);
        }

        $this->newLine();
        $this->info('=====================================');
        $this->info('🎉 Demo Data Successfully Configured! 🎉');
        $this->info('=====================================');
        $this->info('Check your dashboard to see the live updates.');
    }

    private function setupTesla(ParkingSession $session)
    {
        // Tesla scenario: Just parked for a while (2 hours). Still ENTER.
        // User will simulate exit to trigger the alert.
        $session->update([
            'entry_time' => now()->subHours(2),
            'status'     => ParkingStatus::ENTER->value,
            'exit_time'  => null,
            'amount_due' => 0.00,
            'grace_end_time' => null,
        ]);
        $this->info("✓ Setup [Tesla] (Plate: {$session->license_plate}) - Waiting for Mismatch Exit Alert.");
    }

    private function setupGracePeriodCar(ParkingSession $session)
    {
        // Grace Period Expired: Paid, but grace ended 10 minutes ago.
        $entryTime = now()->subHours(3);
        $paymentTime = now()->subMinutes(25); // Paid 25 mins ago
        $graceEndTime = $paymentTime->copy()->addMinutes(config('parking.grace_period_minutes', 15)); // Expired 10 mins ago

        $session->update([
            'entry_time' => $entryTime,
            'status'     => ParkingStatus::PAID->value,
            'exit_time'  => null,
            'grace_end_time' => $graceEndTime,
        ]);

        $amountDue = $session->calculateParkingFee($paymentTime);
        $session->update(['amount_due' => $amountDue]);

        PaymentReceipt::create([
            'parking_session_id' => $session->id,
            'receipt_number'     => 'RCP-' . strtoupper(Str::random(8)),
            'total_amount'       => $amountDue,
            'payment_date'       => $paymentTime,
            'payment_method'     => 'E-WALLET',
            'payment_type'       => 'initial',
        ]);
        $this->info("✓ Setup [Grace Period Car] (Plate: {$session->license_plate}) - Grace period expired 10 mins ago.");
    }

    private function setupFreeExitCar(ParkingSession $session)
    {
        // Entered 5 minutes ago. Should be FREE.
        $session->update([
            'entry_time' => now()->subMinutes(5),
            'status'     => ParkingStatus::ENTER->value,
            'exit_time'  => null,
            'amount_due' => 0.00,
            'grace_end_time' => null,
        ]);
        $this->info("✓ Setup [Free Exit Car] (Plate: {$session->license_plate}) - Entered 5 mins ago (FREE).");
    }

    private function setupNormalLiveCar(ParkingSession $session)
    {
        // Entered 3 hours ago, still inside, unpaid.
        $session->update([
            'entry_time' => now()->subHours(3),
            'status'     => ParkingStatus::ENTER->value,
            'exit_time'  => null,
            'amount_due' => 0.00,
            'grace_end_time' => null,
        ]);
        $this->info("✓ Setup [Normal Live Car] (Plate: {$session->license_plate}) - Entered 3 hours ago.");
    }

    private function setupWeekCar(ParkingSession $session)
    {
        // Completed session within the last 7 days
        $daysAgo = rand(1, 6);
        $entryTime = now()->subDays($daysAgo)->subHours(rand(1, 8));
        $exitTime = $entryTime->copy()->addHours(rand(1, 5))->addMinutes(rand(10, 50));
        
        $this->completeSession($session, $entryTime, $exitTime);
        $this->info("✓ Setup [This Week] (Plate: {$session->license_plate}) - Completed {$daysAgo} days ago.");
    }

    private function setupMonthCar(ParkingSession $session)
    {
        // Completed session between 15 and 70 days ago
        $daysAgo = rand(15, 70);
        $entryTime = now()->subDays($daysAgo)->subHours(rand(1, 8));
        $exitTime = $entryTime->copy()->addHours(rand(1, 5))->addMinutes(rand(10, 50));

        $this->completeSession($session, $entryTime, $exitTime);
        $this->info("✓ Setup [Past Month] (Plate: {$session->license_plate}) - Completed {$daysAgo} days ago.");
    }

    private function completeSession(ParkingSession $session, Carbon $entryTime, Carbon $exitTime)
    {
        $session->update([
            'entry_time' => $entryTime,
            'status'     => ParkingStatus::COMPLETED->value,
            'exit_time'  => $exitTime,
            'grace_end_time' => $exitTime, // they exited exactly when grace ended or similar
        ]);

        // Payment date is usually 5 minutes before exit
        $paymentDate = $exitTime->copy()->subMinutes(5);
        $amountDue = $session->calculateParkingFee($paymentDate);
        $session->update(['amount_due' => $amountDue]);

        $methods = ['CREDIT_CARD', 'CASH', 'E-WALLET'];
        $types = ['KIOSK', 'MOBILE_APP', 'MANUAL'];

        PaymentReceipt::create([
            'parking_session_id' => $session->id,
            'receipt_number'     => 'RCP-' . strtoupper(Str::random(8)),
            'total_amount'       => $amountDue,
            'payment_date'       => $paymentDate,
            'payment_method'     => $methods[array_rand($methods)],
            'payment_type'       => $types[array_rand($types)],
        ]);
    }
}
