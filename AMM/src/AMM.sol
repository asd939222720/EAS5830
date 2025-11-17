// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/access/AccessControl.sol"; //This allows role-based access control through _grantRole() and the modifier onlyRole
import "@openzeppelin/contracts/token/ERC20/ERC20.sol"; //This contract needs to interact with ERC20 tokens

contract AMM is AccessControl{
    bytes32 public constant LP_ROLE = keccak256("LP_ROLE");
	uint256 public invariant;
	address public tokenA;
	address public tokenB;
	uint256 feebps = 3; //The fee in basis points (i.e., the fee should be feebps/10000)

	event Swap( address indexed _inToken, address indexed _outToken, uint256 inAmt, uint256 outAmt );
	event LiquidityProvision( address indexed _from, uint256 AQty, uint256 BQty );
	event Withdrawal( address indexed _from, address indexed recipient, uint256 AQty, uint256 BQty );

	/*
		Constructor sets the addresses of the two tokens
	*/
    constructor( address _tokenA, address _tokenB ) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender );
        _grantRole(LP_ROLE, msg.sender);

		require( _tokenA != address(0), 'Token address cannot be 0' );
		require( _tokenB != address(0), 'Token address cannot be 0' );
		require( _tokenA != _tokenB, 'Tokens cannot be the same' );
		tokenA = _tokenA;
		tokenB = _tokenB;

    }


	function getTokenAddress( uint256 index ) public view returns(address) {
		require( index < 2, 'Only two tokens' );
		if( index == 0 ) {
			return tokenA;
		} else {
			return tokenB;
		}
	}

	/*
		The main trading functions
		
		User provides sellToken and sellAmount

		The contract must calculate buyAmount using the formula:
	*/
	function tradeTokens( address sellToken, uint256 sellAmount ) public {
		require( invariant > 0, 'Invariant must be nonzero' );
		require( sellToken == tokenA || sellToken == tokenB, 'Invalid token' );
		require( sellAmount > 0, 'Cannot trade 0' );
		require( invariant > 0, 'No liquidity' );
		uint256 qtyA;
		uint256 qtyB;
		uint256 swapAmt;

		//YOUR CODE HERE

        uint256 reserveA = ERC20(tokenA).balanceOf(address(this));
        uint256 reserveB = ERC20(tokenB).balanceOf(address(this));
		
		uint256 effectiveIn = sellAmount * (10000 - feebps) / 10000;
		
        if (sellToken == tokenA) {
            require(reserveA > 0 && reserveB > 0, "Empty pool");
            uint256 k = reserveA * reserveB;

            uint256 newReserveA_eff = reserveA + effectiveIn;
            uint256 newReserveB_eff = k / newReserveA_eff;

            swapAmt = reserveB - newReserveB_eff;
            require(swapAmt > 0 && swapAmt < reserveB, "Bad swap amount");

            ERC20(tokenA).transferFrom(msg.sender, address(this), sellAmount);
            ERC20(tokenB).transfer(msg.sender, swapAmt);

            qtyA = sellAmount;
            qtyB = swapAmt;

            emit Swap(tokenA, tokenB, qtyA, qtyB);

        } else {
            require(reserveA > 0 && reserveB > 0, "Empty pool");
            uint256 k = reserveA * reserveB;

            uint256 newReserveB_eff = reserveB + effectiveIn;
            uint256 newReserveA_eff = k / newReserveB_eff;

            swapAmt = reserveA - newReserveA_eff;
            require(swapAmt > 0 && swapAmt < reserveA, "Bad swap amount");

            ERC20(tokenB).transferFrom(msg.sender, address(this), sellAmount);
            ERC20(tokenA).transfer(msg.sender, swapAmt);

            qtyA = swapAmt;
            qtyB = sellAmount;

            emit Swap(tokenB, tokenA, qtyB, qtyA);
        }


		uint256 new_invariant = ERC20(tokenA).balanceOf(address(this))*ERC20(tokenB).balanceOf(address(this));
		require( new_invariant >= invariant, 'Bad trade' );
		invariant = new_invariant;
	}

	/*
		Use the ERC20 transferFrom to "pull" amtA of tokenA and amtB of tokenB from the sender
	*/
	function provideLiquidity( uint256 amtA, uint256 amtB ) public {
		require( amtA > 0 || amtB > 0, 'Cannot provide 0 liquidity' );
		
        if (amtA > 0) {
            ERC20(tokenA).transferFrom(msg.sender, address(this), amtA);
        }
        if (amtB > 0) {
            ERC20(tokenB).transferFrom(msg.sender, address(this), amtB);
        }
		
		
		uint256 balA = ERC20(tokenA).balanceOf(address(this));
        uint256 balB = ERC20(tokenB).balanceOf(address(this));
        invariant = balA * balB;
		
		emit LiquidityProvision( msg.sender, amtA, amtB );
	}

	/*
		Use the ERC20 transfer function to send amtA of tokenA and amtB of tokenB to the target recipient
		The modifier onlyRole(LP_ROLE) 
	*/
	function withdrawLiquidity( address recipient, uint256 amtA, uint256 amtB ) public onlyRole(LP_ROLE) {
		require( amtA > 0 || amtB > 0, 'Cannot withdraw 0' );
		require( recipient != address(0), 'Cannot withdraw to 0 address' );
		if( amtA > 0 ) {
			ERC20(tokenA).transfer(recipient,amtA);
		}
		if( amtB > 0 ) {
			ERC20(tokenB).transfer(recipient,amtB);
		}
		invariant = ERC20(tokenA).balanceOf(address(this))*ERC20(tokenB).balanceOf(address(this));
		emit Withdrawal( msg.sender, recipient, amtA, amtB );
	}


}
