<?php

namespace App\Enums;

enum ParkingStatus: string
{
    case ENTER = 'ENTER';
    case PAID = 'PAID';
    case COMPLETED = 'COMPLETED';
}
