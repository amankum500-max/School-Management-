// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ExamTicketGate {
    mapping(string => bool) public isFeePaid;
    
    // Fee payment confirm karne ke liye (Admin only)
    function confirmFee(string memory rollNo) public {
        isFeePaid[rollNo] = true;
    }

    // Ticket generation se pehle check
    function verifyEligibility(string memory rollNo) public view returns (bool) {
        return isFeePaid[rollNo];
    }
}
