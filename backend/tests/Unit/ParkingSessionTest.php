<?php

namespace Tests\Unit;

use App\Models\ParkingSession;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Config;
use Tests\TestCase; // Use Laravel's TestCase to access config()

class ParkingSessionTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        
        // Mock the configuration for predictable testing
        Config::set('parking.rate_per_hour', 2.00);
        Config::set('parking.free_exit_minutes', 15);
    }

    public function test_free_exit_within_15_minutes()
    {
        $session = new ParkingSession();
        $session->entry_time = Carbon::parse('2026-08-21 10:00:00');
        
        $endTime = Carbon::parse('2026-08-21 10:10:00'); // 10 mins
        $fee = $session->calculateParkingFee($endTime);
        
        $this->assertEquals(0.00, $fee);
    }

    public function test_free_exit_at_exactly_15_minutes()
    {
        $session = new ParkingSession();
        $session->entry_time = Carbon::parse('2026-08-21 10:00:00');
        
        $endTime = Carbon::parse('2026-08-21 10:15:00'); // exactly 15 mins
        $fee = $session->calculateParkingFee($endTime);
        
        $this->assertEquals(0.00, $fee);
    }

    public function test_minimum_charge_at_16_minutes()
    {
        $session = new ParkingSession();
        $session->entry_time = Carbon::parse('2026-08-21 10:00:00');
        
        $endTime = Carbon::parse('2026-08-21 10:16:00'); // 16 mins
        $fee = $session->calculateParkingFee($endTime);
        
        $this->assertEquals(2.00, $fee);
    }

    public function test_charge_for_exactly_one_hour()
    {
        $session = new ParkingSession();
        $session->entry_time = Carbon::parse('2026-08-21 10:00:00');
        
        $endTime = Carbon::parse('2026-08-21 11:00:00'); // 60 mins
        $fee = $session->calculateParkingFee($endTime);
        
        $this->assertEquals(2.00, $fee);
    }

    public function test_charge_rounds_up_to_next_hour()
    {
        $session = new ParkingSession();
        $session->entry_time = Carbon::parse('2026-08-21 10:00:00');
        
        $endTime = Carbon::parse('2026-08-21 11:01:00'); // 61 mins
        $fee = $session->calculateParkingFee($endTime);
        
        $this->assertEquals(4.00, $fee); // 2 hours
    }

    public function test_long_stay_charge()
    {
        $session = new ParkingSession();
        $session->entry_time = Carbon::parse('2026-08-21 10:00:00');
        
        $endTime = Carbon::parse('2026-08-21 15:30:00'); // 330 mins = 5.5 hours -> rounds to 6
        $fee = $session->calculateParkingFee($endTime);
        
        $this->assertEquals(12.00, $fee); // 6 hours
    }
}
